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

import asyncio
import fnmatch
import io
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from autom8y_core.errors import (
    DataServiceError,
    DataServiceUnavailableError,
    DataServiceValidationError,
)
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
    _mask_addr,
    assert_exclusive_tenant_binding,
    harvest_routing_addresses,
)
from autom8_asana.clients.utils.pii import mask_phone_number
from autom8_asana.resolution.gfr.errors import (
    AmbiguousCardinalityError,
    GfrError,
    GuardViolationError,
)

if TYPE_CHECKING:
    from _typeshed import ReadableBuffer

    from autom8_asana.clients.attachments import AttachmentsClient
    from autom8_asana.core.scope import EntityScope
    from autom8_asana.query.engine import QueryEngine
    from autom8_asana.resolution.gfr.truth_source import ByGuidVerifier

logger = get_logger(__name__)


class _PriorTooLargeError(Exception):
    """Internal sentinel (F5): a prior deck exceeded the harvest size cap mid-stream.

    Raised by ``_CappedBuffer.write`` when a streaming download would push the
    buffer past ``constants.MAX_PRIOR_DECK_BYTES``. Never escapes the workflow --
    ``_download_attachment_bytes`` catches it and returns ``None`` (skip this prior).
    """


class _CappedBuffer(io.BytesIO):
    """A ``BytesIO`` that refuses to grow past ``cap`` bytes (F5 streaming guard).

    The attachment download streams chunks into this buffer (``destination.write``);
    if a prior exceeds the cap mid-stream we raise ``_PriorTooLargeError`` rather
    than materialize an unbounded blob in memory. This guards the case where the
    attachment's reported ``size`` is absent or under-reports -- the up-front size
    check in ``_existing_walkthrough_guids`` is the cheap first line; this is the
    hard wall that makes the bound hold regardless of what the size field claims.
    """

    def __init__(self, cap: int) -> None:
        super().__init__()
        self._cap = cap
        self._written = 0

    def write(self, buffer: ReadableBuffer, /) -> int:
        self._written += memoryview(buffer).nbytes
        if self._written > self._cap:
            raise _PriorTooLargeError(self._written)
        return super().write(buffer)


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
    ) -> identity_guard.AnchorResult: ...


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
        onboarding_project_gid: Asana onboarding project GID. Retained as the
            preserved project-level enumeration fallback (the N=1 pilot path) and
            the two-way door to the original single-project sweep.
        calendar_integrations_project_gid: Asana Calendar-Integrations project GID
            (W3). The batch sweep's ACTIVE-section enumeration target; defaults to
            the R-1-census-confirmed constant, constructor-overridable.
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
        calendar_integrations_project_gid: str = constants.CALENDAR_INTEGRATIONS_PROJECT_GID,
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
        self._calendar_integrations_project_gid = calendar_integrations_project_gid

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
        problems = await super().validate_async()

        # F4 -- W1 guard INERT detection (whole-sweep observability). The flag is
        # ENABLED but the W1 GFR by-GUID anchor has no substrate (query_engine
        # unwired). Per-task, that fail-closes every entity to skipped(anchor_unresolved)
        # -- correct and safe, but at SWEEP altitude it means the run attaches NOTHING
        # while reporting "ran clean", indistinguishable from a sweep where every task
        # legitimately lacked an identity path. Surface it LOUDLY as a pre-flight
        # problem (a single ERROR + a validation error string) so an unwired deploy is
        # DETECTABLE -- a dark, inert sweep must never look like a healthy one. This is
        # distinct from the per-task skip: it fires once, at pre-flight, before fan-out.
        if self._query_engine is None:
            logger.error(
                "onboarding_walkthrough_guard_inert",
                reason="query_engine_unwired",
                detail="W1 guard INERT: query_engine unwired -- sweep will skip all tasks",
            )
            problems.append(
                "W1 guard INERT: query_engine unwired -- the GFR by-GUID identity "
                "guard has no substrate, so every task fails closed "
                "(anchor_unresolved) and the sweep attaches nothing. Wire "
                "query_engine before enabling this workflow."
            )
        return problems

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
        """Full enumeration (W3): ACTIVE-section tasks of Calendar-Integrations.

        Implements the abstract hook called by the base ``enumerate_async`` for
        the full (non-targeted) path. Re-points the sweep from the Onboarding
        project default to the Calendar-Integrations project, resolving the
        ACTIVE section BY NAME via ``resolve_section_gids`` -- never a hardcoded
        section GID, and never the Offers ``OFFER_CLASSIFIER`` (the active-set
        definition for THIS sweep is the section literally named "ACTIVE";
        importing the Offers classifier would drag an Offers denominator into a
        Calendar-Integrations sweep -- G-DENOM hygiene).

        Resilience mirrors ``active_offer_enumeration``: a section-resolution
        failure, an empty ACTIVE resolution, OR a partial section-fetch failure
        falls back to the preserved project-level enumeration over the Onboarding
        project (the N=1 pilot path, not regressed). Both project GIDs are
        constructor-overridable (two-way door).
        """
        # Deferred import: keep the enumeration path free of any Offers-domain
        # coupling (section_resolution carries NO OFFER_CLASSIFIER); mirrors the
        # lazy-import discipline of active_offer_enumeration.
        from autom8_asana.automation.workflows.section_resolution import (
            resolve_section_gids,
        )

        try:
            resolved = await resolve_section_gids(
                self._asana_client.sections,
                self._calendar_integrations_project_gid,
                constants.ACTIVE_SECTION_NAMES,
            )
        except Exception:  # noqa: BLE001 -- boundary: section-resolution failure -> project fallback
            logger.warning(
                "onboarding_walkthrough_section_resolution_failed_fallback",
                project_gid=self._calendar_integrations_project_gid,
            )
            return await self._enumerate_project_level(self._onboarding_project_gid)

        if not resolved:
            logger.warning(
                "onboarding_walkthrough_section_resolution_empty_fallback",
                project_gid=self._calendar_integrations_project_gid,
            )
            return await self._enumerate_project_level(self._onboarding_project_gid)

        # Parallel section fetch with bounded concurrency (mirror bridge fan-out cap).
        semaphore = asyncio.Semaphore(5)

        async def _fetch_section(section_gid: str) -> list[Any]:
            async with semaphore:
                fetched: list[Any] = await self._asana_client.tasks.list_async(
                    section=section_gid,
                    opt_fields=["name", "completed", "custom_fields"],
                    completed_since="now",
                ).collect()
                return fetched

        results = await asyncio.gather(
            *[_fetch_section(gid) for gid in resolved.values()],
            return_exceptions=True,
        )

        # Any section fetch failure -> fall back entirely (no partial sweep).
        if any(isinstance(r, Exception) for r in results):
            logger.warning(
                "onboarding_walkthrough_section_fetch_partial_failure_fallback",
                project_gid=self._calendar_integrations_project_gid,
                failed_count=sum(1 for r in results if isinstance(r, Exception)),
            )
            return await self._enumerate_project_level(self._onboarding_project_gid)

        # Flatten, drop completed, dedup by GID, build entities via the shared
        # gate-input reader (calendar_provider + office_phone off each task).
        seen_gids: set[str] = set()
        entities: list[dict[str, Any]] = []
        for section_tasks in results:
            assert isinstance(section_tasks, list)  # guarded by the early-exit above
            for task in section_tasks:
                if getattr(task, "completed", False) or task.gid in seen_gids:
                    continue
                seen_gids.add(task.gid)
                entities.append(self._task_to_entity(task))

        logger.info(
            "onboarding_walkthrough_section_targeted_enumeration",
            project_gid=self._calendar_integrations_project_gid,
            sections_targeted=len(resolved),
            tasks_enumerated=len(entities),
        )
        return entities

    async def _enumerate_project_level(self, project_gid: str) -> list[dict[str, Any]]:
        """Project-level enumeration -- the preserved Onboarding N=1 pilot path.

        The verbatim pre-W3 ``enumerate_entities`` body, parameterized by project
        GID so it serves BOTH as the section-resolution fallback and as the
        constructor-overridable two-way door to the original single-project sweep.
        """
        page_iterator = self._asana_client.tasks.list_async(
            project=project_gid,
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
        except DataServiceError as exc:
            # FR-2 (resolve): a malformed / non-200 data-service body surfaces as the
            # DataServiceError base (data family). NAMED failed reason (mirrors the DSU
            # leg), never the generic terminal swallow. Subclass-before-base: the DSU
            # leg above precedes this base leg.
            logger.error(
                "onboarding_walkthrough_resolve_data_error",
                task_gid=gid,
                office_phone=masked,
                error=str(exc),
            )
            return BridgeOutcome(
                gid=gid,
                status="failed",
                error=WorkflowItemError(
                    item_id=gid,
                    error_type="resolve_data_error",
                    message=str(exc),
                    recoverable=True,
                ),
            )
        except ValueError as exc:
            # FR-2 (resolve): the SDK composes the gated address via
            # ``format_routing_address(business.guid)`` which raises ``ValueError`` on a
            # non-canonical STORED guid (routing.py:105) -- the R1 data-shape candidate.
            # Disjoint from the DataService hierarchy (order-free); non-recoverable.
            logger.error(
                "onboarding_walkthrough_resolve_invalid",
                task_gid=gid,
                office_phone=masked,
                error=str(exc),
            )
            return BridgeOutcome(
                gid=gid,
                status="failed",
                error=WorkflowItemError(
                    item_id=gid,
                    error_type="resolve_invalid_input",
                    message=str(exc),
                    recoverable=False,
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
            anchor_result = await self._company_id_anchor(
                task_gid=gid,
                client=self._asana_client,
                query_engine=self._query_engine,
                verifier=self._verifier,
            )
        except GuardViolationError as exc:
            # FAIL-CLOSED + LOUD (F3): a GuardViolationError means a plan element
            # tried to reach the tenant-identity field via the office_phone value-join
            # -- the v1 PHI-leak trap (errors.py:80). This is UNREACHABLE by
            # construction (the identity path is gid-exact); a raise here is a hard
            # STRUCTURAL-DRIFT signal, not a routine missing path. Skip like any anchor
            # failure, but emit a DISTINCT reason at ERROR so the trap-reintroduction
            # signal is never masked inside benign anchor_unresolved noise.
            logger.error(
                "onboarding_walkthrough_skipped",
                task_gid=gid,
                reason="guard_violation",
                error=str(exc),
            )
            return BridgeOutcome(gid=gid, status="skipped", reason="guard_violation")
        except AmbiguousCardinalityError as exc:
            # FAIL-CLOSED + LOUD (F3): the gid-exact by-GUID anchor returned a
            # non-single-row result (INVARIANT I5) -- the identity read was ambiguous,
            # a data-integrity signal (duplicate/garbled Business rows for one gid),
            # NOT a benign absent path. Distinct reason at ERROR so it is diagnosable
            # apart from the routine no-identity-path skip.
            logger.error(
                "onboarding_walkthrough_skipped",
                task_gid=gid,
                reason="ambiguous_anchor",
                error=str(exc),
            )
            return BridgeOutcome(gid=gid, status="skipped", reason="ambiguous_anchor")
        except GfrError as exc:
            # FAIL-CLOSED (routine): GFR cannot independently anchor this task's tenant
            # -- the BENIGN no-identity-path case (UnresolvedError: no parent chain to a
            # Business root, or the anchored row is absent). This IS an expected runtime
            # condition for a task that simply has no identity path, so it stays a
            # WARNING + anchor_unresolved. The structural/integrity signals above are
            # peeled off FIRST (subclasses precede the base) so they never hide here.
            logger.warning(
                "onboarding_walkthrough_skipped",
                task_gid=gid,
                reason="anchor_unresolved",
                error=str(exc),
            )
            return BridgeOutcome(gid=gid, status="skipped", reason="anchor_unresolved")
        except DataServiceUnavailableError as exc:
            # FR-2 (anchor): a transient infra fault (timeout/5xx/circuit) from the
            # by-GUID anchor (truth_source.py:68, UNWRAPPED). The DataService family is
            # DISJOINT from the GFR family above, so it is peeled off here as a NAMED
            # ``failed`` (mirrors the resolve leg) -- never mistaken for the benign
            # no-identity-path skip. Subclasses (this + anchor_invalid) precede the base.
            logger.error(
                "onboarding_walkthrough_anchor_unavailable",
                task_gid=gid,
                error=str(exc),
            )
            return BridgeOutcome(
                gid=gid,
                status="failed",
                error=WorkflowItemError(
                    item_id=gid,
                    error_type="anchor_unavailable",
                    message=str(exc),
                    recoverable=True,
                ),
            )
        except DataServiceValidationError as exc:
            # FR-2 (anchor): a 4xx data-shape fault (e.g. INVALID_BUSINESS_GUID_FORMAT,
            # data_service.py:763) -- the R1 data-shape candidate. Non-recoverable.
            logger.error(
                "onboarding_walkthrough_anchor_invalid",
                task_gid=gid,
                error=str(exc),
            )
            return BridgeOutcome(
                gid=gid,
                status="failed",
                error=WorkflowItemError(
                    item_id=gid,
                    error_type="anchor_invalid",
                    message=str(exc),
                    recoverable=False,
                ),
            )
        except DataServiceError as exc:
            # FR-2 (anchor): the DataService base -- the safety net WITHIN the data
            # family (a malformed body, or a future sibling reaching this path). NAMED
            # ``failed``, never swallowed. Auth-family classes are NOT DataServiceError
            # (siblings under TransportError) -> they deliberately fall through to the
            # shared runner's logged terminal net where R2 self-identifies.
            logger.error(
                "onboarding_walkthrough_anchor_data_error",
                task_gid=gid,
                error=str(exc),
            )
            return BridgeOutcome(
                gid=gid,
                status="failed",
                error=WorkflowItemError(
                    item_id=gid,
                    error_type="anchor_data_error",
                    message=str(exc),
                    recoverable=True,
                ),
            )

        # The certified Source-B tenant guid + the GFR truth-tier the anchor resolved
        # at (CACHE vs VERIFIED). Both are consumed below: the guid for the cross-tenant
        # gid-exact compare, the tier for the C-BN1-05 success audit record.
        anchored_company_id = anchor_result.company_id

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
            # F1 -- TENANT-ISOLATION REAP. Before SKIPping (target already attached),
            # reap any FOREIGN-guid prior: a deck for a DIFFERENT tenant whose
            # delete-old soft-failed on a prior run (mixins.py per-item swallow). On
            # the MINT path the upload-first glob delete reaps such priors; the
            # already-attached SKIP path never runs it, so a wrong-tenant deck would
            # otherwise persist on the task INDEFINITELY -- the exact misroute residue
            # this initiative exists to kill. Idempotent: a no-op when no foreign prior
            # exists; scoped strictly to attachments NOT carrying the target guid.
            await self._reap_foreign_priors(gid, existing_by_guid, keep_guid=target_guid)
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

            # C-BN1-05 (SEC-N2 §3) -- the affirmative per-task SUCCESS audit record:
            # the structural batch replacement for the retired N=1 human attestation
            # line, reached ONLY after W1 passed (resolve-correctness) AND T7 passed
            # (exclusive tenant binding) AND the upload succeeded. Binds the automation
            # identity, the task, the MASKED tenant company_id (Source B) + MASKED gated
            # routing address (Source A -- a routing-secret bearer capability, NEVER
            # logged in full), the W1 anchor-basis TIER (CACHE vs VERIFIED, read from
            # the GFR provenance the anchor resolved at), and a timestamp. This is the
            # after-the-fact misroute-detection + C-BN1-08 sampled-CRR-1 reconcile
            # substrate; by construction ABSENT on every skip/fail path (those return
            # upstream of here).
            logger.info(
                "onboarding_walkthrough_upload_succeeded",
                workflow_id=self.workflow_id,
                task_gid=gid,
                filename=out_filename,
                size_bytes=len(frozen_bytes),
                company_id=identity_guard.mask_guid(anchored_company_id),
                gated_address=_mask_addr(gated_address),
                anchor_tier=anchor_result.tier.name,
                attached_at=datetime.now(UTC).isoformat(),
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
            ``{embedded_guid -> [attachment, ...]}`` for all prior walkthrough decks,
            with EACH attachment appearing AT MOST ONCE per guid (F2). Empty when the
            task carries no ``walkthrough_*.html`` (the no-prior arm).
        """
        # ``by_gid``: guid -> {attachment.gid -> attachment}. Keying the inner level on
        # the attachment gid is the F2 fix: ``harvest_routing_addresses`` returns the
        # DISTINCT set of routing-address strings, so a single deck embedding the SAME
        # guid in two case-variants (e.g. ``ABC@...`` and ``abc@...``) yields two set
        # members that both lower() to one guid. Appending blindly counted that ONE
        # attachment as TWO priors -> the >1 dedupe-down then deleted the only real
        # deck and skipped the re-mint (self-delete). Collapsing on attachment gid here
        # makes one attachment count once per guid, regardless of case-variant
        # multiplicity (and is also robust to a paginated double-list of the same gid).
        by_gid: dict[str, dict[str, Any]] = {}
        page_iter = self._attachments_client.list_for_task_async(
            task_gid,
            opt_fields=["name", "created_at", "size"],
        )
        async for att in page_iter:
            name = getattr(att, "name", None) or ""
            if not fnmatch.fnmatch(name, constants.ATTACHMENT_GLOB):
                continue
            size = getattr(att, "size", None)
            if isinstance(size, int) and size > constants.MAX_PRIOR_DECK_BYTES:
                # F5 (cheap up-front guard): an oversized prior is not a deck this
                # workflow minted; skip the harvest rather than pull MBs into memory.
                logger.warning(
                    "onboarding_walkthrough_prior_oversize_skipped",
                    task_gid=task_gid,
                    attachment_gid=att.gid,
                    size_bytes=size,
                    cap_bytes=constants.MAX_PRIOR_DECK_BYTES,
                )
                continue
            raw = await self._download_attachment_bytes(att.gid)
            if raw is None:
                # F5: this prior could not be harvested (download failure, or it
                # streamed past the cap). Skip THIS prior only -- one bad prior must
                # never abort the whole task's idempotency check. Worst case the target
                # re-mints and the next run's dedupe-down reaps the residue (the
                # presence-gate keeps it non-compounding); never a wrong-tenant attach.
                continue
            for routing_addr in harvest_routing_addresses(raw):
                guid = routing_addr.split("@", 1)[0].lower()
                by_gid.setdefault(guid, {})[att.gid] = att
        return {guid: list(atts.values()) for guid, atts in by_gid.items()}

    async def _download_attachment_bytes(self, attachment_gid: str) -> bytes | None:
        """Fetch a prior attachment's bytes for the W2 embedded-guid harvest.

        The AttachmentsClient download surface writes to a ``destination`` BinaryIO
        and returns a path/None (it does NOT return bytes), so this thin wrapper
        streams into an in-memory buffer and returns the bytes (UV-P-W2 discharge --
        the byte-download surface exists; it is destination-based, not bytes-returning).

        F5: the buffer is size-CAPPED (``_CappedBuffer``) so a prior that streams past
        ``constants.MAX_PRIOR_DECK_BYTES`` aborts mid-download instead of materializing
        an unbounded blob; and the download is wrapped so a single failed/oversized
        prior returns ``None`` (skip it) rather than propagating and aborting the
        task's whole idempotency check.

        Args:
            attachment_gid: the prior attachment's gid.

        Returns:
            The raw deck bytes (for ``harvest_routing_addresses``), or ``None`` when
            the prior is oversized or undownloadable (caller skips that prior).
        """
        buffer = _CappedBuffer(constants.MAX_PRIOR_DECK_BYTES)
        try:
            await self._attachments_client.download_async(attachment_gid, destination=buffer)
        except _PriorTooLargeError:
            logger.warning(
                "onboarding_walkthrough_prior_oversize_truncated",
                attachment_gid=attachment_gid,
                cap_bytes=constants.MAX_PRIOR_DECK_BYTES,
            )
            return None
        except Exception as exc:  # noqa: BLE001 -- boundary: one bad prior must not abort the idempotency check
            logger.warning(
                "onboarding_walkthrough_prior_download_failed",
                attachment_gid=attachment_gid,
                error=str(exc),
            )
            return None
        return buffer.getvalue()

    async def _reap_foreign_priors(
        self,
        task_gid: str,
        existing_by_guid: dict[str, list[Any]],
        *,
        keep_guid: str,
    ) -> int:
        """Delete prior walkthrough decks whose embedded guid != ``keep_guid`` (F1).

        The already-attached SKIP path does not run the upload-first glob delete, so a
        FOREIGN-tenant prior (a deck for a DIFFERENT guid whose delete soft-failed on a
        prior run) would persist on the task indefinitely -- a wrong-tenant artifact,
        the exact misroute residue this initiative exists to kill. This reaps every
        prior carrying a guid OTHER than ``keep_guid``, soft-failing per item (mirrors
        ``_delete_old_attachments`` -- one stuck delete never aborts the reap).

        Strictly scoped: an attachment that ALSO carries the target guid (a
        contaminated multi-address deck, which T7 blocks at mint) is NEVER reaped --
        the keep-guid attachments are excluded by gid so the legitimate deck can never
        be deleted here. Idempotent: a no-op when no foreign prior exists.

        Args:
            task_gid: the task being processed (for structured logging).
            existing_by_guid: the W2 0a harvest map (embedded-guid -> [attachment]).
            keep_guid: the target tenant guid whose decks must be preserved.

        Returns:
            The number of foreign attachments successfully deleted (for tests/metrics).
        """
        keep_att_gids = {att.gid for att in existing_by_guid.get(keep_guid, [])}
        # att.gid -> (attachment, one foreign guid it is harvested under, for masked
        # logging). Dedup on att.gid so a prior harvested under several foreign guids
        # is reaped exactly once.
        foreign_atts: dict[str, tuple[Any, str]] = {}
        for guid, atts in existing_by_guid.items():
            if guid == keep_guid:
                continue
            for att in atts:
                if att.gid not in keep_att_gids:
                    foreign_atts.setdefault(att.gid, (att, guid))
        if not foreign_atts:
            return 0

        deleted = 0
        for att, foreign_guid in foreign_atts.values():
            try:
                await self._attachments_client.delete_async(att.gid)
                deleted += 1
                # WARNING, not INFO: a foreign prior surviving to this path means a
                # prior delete-old soft-failed and a wrong-tenant deck lingered. Reaping
                # it is a self-heal, but the lingering itself is an anomaly worth
                # surfacing (guids masked, never spilled in full).
                logger.warning(
                    "onboarding_walkthrough_foreign_prior_reaped",
                    task_gid=task_gid,
                    attachment_gid=att.gid,
                    attachment_name=getattr(att, "name", None),
                    foreign_guid=identity_guard.mask_guid(foreign_guid),
                )
            except Exception as exc:  # noqa: BLE001 -- boundary: reap delete soft-fails per item
                logger.warning(
                    "onboarding_walkthrough_foreign_reap_failed",
                    task_gid=task_gid,
                    attachment_gid=att.gid,
                    error=str(exc),
                )
        return deleted

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
