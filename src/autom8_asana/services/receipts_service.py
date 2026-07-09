"""Service orchestration for the EBI OI-2 receipts route.

Threads an internal, redacted forwarding-lifecycle receipt onto a clinic's
Business task as an Asana comment. Three phases:

  1. RESOLVE  ``company_id`` -> the single Business ``task_gid`` via a
     store-independent LIVE ``tasks/search`` on the "Company ID" custom field,
     filtered to the Businesses project, FAIL-CLOSED on zero/ambiguous matches
     (the ``_business_gid_by_phone`` idiom adapted from Office Phone). This is
     the decisive design choice (FORK-R / ADR D-3): the cache-backed
     ``SearchService`` fails OPEN-as-not-found on a cold cache, which in a
     receipts route would silently drop a real clinic's receipt. Live search is
     authoritative on every call.

  2. DEDUP    scan the task's existing stories for THIS receipt's marker
     (the ``link_on_play`` marker-in-text pattern). Present ⇒ skip (idempotent).

  3. POST     ``create_comment`` (bot PAT) with the marker-prefixed body.

D12: the comment threads onto the TEAM's INTERNAL Business task -- never a
client-facing message. The provider adds no PII (the consumer already redacts).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.api.routes.receipts_models import ReceiptKind, ReceiptPostResponse
from autom8_asana.core.project_registry import BUSINESS_PROJECT
from autom8_asana.domain.forwarding_stage import (
    RECEIPT_KIND_TO_STAGE,
    ForwardingStage,
    StageDisposition,
    StageRankTable,
    StageTransitionValidator,
)
from autom8_asana.services.ci_task_resolution import (
    UnknownStage as _UnknownStage,
)
from autom8_asana.services.ci_task_resolution import (
    read_current_stage as _read_current_stage_impl,
)
from autom8_asana.services.ci_task_resolution import (
    resolve_ci_task_gid as _resolve_ci_task_gid_impl,
)

if TYPE_CHECKING:
    from autom8_asana import AsanaClient

logger = get_logger(__name__)

# The Businesses-project discriminator: a Business task's Company ID lives here.
# Offer/Process/Commission rows can also carry a Company ID cascade, so the
# project membership is the deterministic filter (same anchor the resolver
# hierarchy walk and _business_gid_by_phone use).
_BUSINESSES_PROJECT_GID = BUSINESS_PROJECT  # "1200653012566782"

# The Calendar-Integrations second-resolution (company_id -> CI task, where the
# Forwarding-Stage field lives) is extracted to ``services.ci_task_resolution``
# and shared with the S4 backfill; the project-GID constant now lives there.

_MARKER_PREFIX = "RCPT"


# ``_UnknownStage`` is the CI-task current-stage sentinel, extracted to
# ``services.ci_task_resolution`` (shared with the S4 backfill). Imported above
# under its original private name so every internal reference + the S1 receipts
# tests continue to see ``_UnknownStage`` unchanged (behaviour-preserving).


@dataclass(frozen=True)
class ForwardingStageWriteConfig:
    """Config for the config-gated Forwarding-Stage write leg (ADR-FS-004/005).

    All values are operator-sourced (see ApiSettings.forwarding_stage_*). The
    write leg is INERT (a NO-OP, byte-identical to the comment-only baseline)
    unless ``enabled`` is True AND ``field_gid`` is non-empty AND
    ``option_gids`` is populated -- the dark-posture gate.

    ``option_gids`` maps a ForwardingStage value ("Verified") -> Asana enum-option
    GID; it is the ONLY place option GIDs live (never hardcoded in code).
    ``inactive_disposition`` is the data-driven Inactive ruling (default PARKED).
    """

    enabled: bool = False
    field_gid: str = ""
    option_gids: dict[str, str] = field(default_factory=dict)
    inactive_disposition: StageDisposition = StageDisposition.PARKED

    @property
    def is_active(self) -> bool:
        """True iff the write leg should attempt an advance (all gates satisfied)."""
        return bool(self.enabled and self.field_gid and self.option_gids)

    @classmethod
    def from_settings(
        cls,
        *,
        enabled: bool,
        field_gid: str,
        option_gids: dict[str, str],
        disposition: dict[str, str],
    ) -> ForwardingStageWriteConfig:
        """Build from the raw ApiSettings values (fail-safe on a bad disposition).

        An unrecognized ``Inactive`` disposition string falls back to the safe
        PARKED default rather than raising -- a config typo must not crash the
        receipts route (the comment leg is correctness-critical).
        """
        raw = (disposition or {}).get("Inactive", StageDisposition.PARKED.value)
        try:
            inactive = StageDisposition(raw)
        except ValueError:
            logger.warning(
                "forwarding_stage_disposition_invalid",
                extra={"raw": raw, "fallback": StageDisposition.PARKED.value},
            )
            inactive = StageDisposition.PARKED
        return cls(
            enabled=enabled,
            field_gid=field_gid,
            option_gids=dict(option_gids or {}),
            inactive_disposition=inactive,
        )


class ReceiptResolutionError(RuntimeError):
    """Base for company-resolution failures (mapped to 4xx/503 in the route)."""


class CompanyIdFieldUnconfigured(ReceiptResolutionError):
    """The "Company ID" custom-field definition GID is not configured (OI-2b).

    Mapped to 503 -- an activation prerequisite, not a client error. The route
    refuses to guess a receiver rather than resolving against an unknown field.
    """


class CompanyNotResolved(ReceiptResolutionError):
    """No Business task carries this ``company_id`` (fail-closed 404).

    Never guess, never thread onto a fallback task.
    """


class CompanyAmbiguous(ReceiptResolutionError):
    """More than one Business task carries this ``company_id`` (fail-closed 409).

    Never pick a receiver silently.
    """

    def __init__(self, company_id: str, gids: list[str]) -> None:
        self.company_id = company_id
        self.gids = gids
        super().__init__(
            f"{len(gids)} Business tasks match company_id after the "
            f"Businesses-project discriminator; refusing to pick a receiver "
            f"silently. gids={gids}"
        )


class NoWorkspaceConfigured(ReceiptResolutionError):
    """No default workspace on the client (mapped to 503; refuse rather than guess)."""


def _marker(company_id: str, kind: str, bucket: str) -> str:
    """Deterministic idempotency marker embedded as a prefix line in the comment.

    Grammar ``RCPT|<company_id>|<kind>|<bucket>``. The three once-per-clinic
    lifecycle kinds use an empty bucket (idempotent forever); ``nudge`` uses a
    coarse UTC-date bucket so it re-fires once per clinic per day (the
    loud-recurring intent). See ADR D-5 / OI-2a watch.
    """
    return f"{_MARKER_PREFIX}|{company_id}|{kind}|{bucket}"


def _bucket_for(kind: str) -> str:
    """Bucket component of the marker (see :func:`_marker`)."""
    if kind == ReceiptKind.NUDGE.value:
        return datetime.now(UTC).strftime("%Y-%m-%d")
    return ""


def _stage_display(current: ForwardingStage | _UnknownStage | None) -> str | None:
    """Log-safe rendering of a read current stage (handles the unknown sentinel)."""
    if current is None:
        return None
    if isinstance(current, ForwardingStage):
        return current.value
    return f"unknown:{current.option_gid}"


class ReceiptsService:
    """Resolve -> dedup -> post orchestration for a single receipt.

    Optionally (config-gated, default OFF) also advances the Forwarding-Stage
    field on the clinic's Calendar Integrations task after the comment is
    threaded (ADR-FS-004). The stage-advance leg is best-effort and no-throw: it
    NEVER fails the receipt route (the comment is the correctness-critical leg).
    """

    def __init__(
        self,
        client: AsanaClient,
        *,
        company_id_field_gid: str,
        stage_write_config: ForwardingStageWriteConfig | None = None,
    ) -> None:
        self._client = client
        self._company_id_field_gid = company_id_field_gid
        self._stage_cfg = stage_write_config or ForwardingStageWriteConfig()
        self._stage_validator = StageTransitionValidator(
            StageRankTable(),
            inactive_disposition=self._stage_cfg.inactive_disposition,
        )

    async def _resolve_business_gid(self, company_id: str) -> str:
        """Resolve ``company_id`` -> the single Business ``task_gid`` (fail-closed).

        Store-independent LIVE ``tasks/search`` keyed on the Company ID
        custom-field value, filtered to the Businesses project. Raises
        :class:`CompanyNotResolved` on zero matches (404),
        :class:`CompanyAmbiguous` on >1 (409),
        :class:`CompanyIdFieldUnconfigured` (503) when the field GID is absent,
        :class:`NoWorkspaceConfigured` (503) when no workspace is set.
        """
        if not self._company_id_field_gid:
            raise CompanyIdFieldUnconfigured(
                "ASANA_API_COMPANY_ID_FIELD_GID is not configured; refusing to "
                "resolve a receipt receiver against an unknown custom field "
                "(OI-2b activation prerequisite)."
            )

        workspace_gid = self._client.default_workspace_gid
        if not workspace_gid:
            raise NoWorkspaceConfigured(
                "no default workspace configured for the Business lookup; "
                "refusing rather than guessing a workspace."
            )

        data = await self._client.http.get(
            f"/workspaces/{workspace_gid}/tasks/search",
            params={
                f"custom_fields.{self._company_id_field_gid}.value": company_id,
                "opt_fields": "name,projects.gid",
            },
        )
        # http.get unwraps the {"data": ...} envelope; on a list result the
        # else-branch takes it, on a dict the .get does -- same dual-handling as
        # _business_gid_by_phone (defensive against envelope-shape drift).
        results = data.get("data", []) if isinstance(data, dict) else (data or [])
        matches = [
            t
            for t in results
            if any(
                (p or {}).get("gid") == _BUSINESSES_PROJECT_GID for p in (t.get("projects") or [])
            )
        ]
        if not matches:
            raise CompanyNotResolved(f"no Business task carries company_id={company_id!r}")
        if len(matches) > 1:
            raise CompanyAmbiguous(company_id, [str(m.get("gid")) for m in matches])
        gid = matches[0].get("gid")
        if gid is None:  # pragma: no cover - Asana always returns a gid on a hit
            raise CompanyNotResolved(
                f"matched Business for company_id={company_id!r} but it carries no gid"
            )
        return str(gid)

    async def thread_receipt(self, *, company_id: str, kind: str, body: str) -> ReceiptPostResponse:
        """Resolve, dedup, and post one receipt. Raises on Asana wire error.

        The marker is a hidden-ish prefix LINE on the comment text; the
        operator's glance still reads the receipt body below it.
        """
        business_gid = await self._resolve_business_gid(company_id)

        marker = _marker(company_id, kind, _bucket_for(kind))
        text = f"{marker}\n{body}"

        # Idempotency: list stories, skip if this marker already present.
        stories = await self._client.stories.list_for_task_async(
            business_gid, opt_fields=["text", "created_at"]
        ).collect()
        existing = next((s for s in stories if marker in (s.text or "")), None)
        if existing is not None:
            logger.info(
                "forwarding_receipt_skipped_duplicate",
                extra={"business_gid": business_gid, "kind": kind},
            )
            # Even on a duplicate comment, converge the stage (idempotent: the
            # validator NO-OPs when the field already reflects the event). This
            # keeps the board correct if a comment landed but a prior advance was
            # skipped (e.g. the switch was flipped ON between deliveries).
            await self._advance_stage(company_id, kind)
            return ReceiptPostResponse(
                business_gid=business_gid,
                story_gid=existing.gid,
                outcome="skipped_duplicate",
            )

        story = await self._client.stories.create_comment_async(task=business_gid, text=text)
        logger.info(
            "forwarding_receipt_posted",
            extra={"business_gid": business_gid, "story_gid": story.gid, "kind": kind},
        )
        # Config-gated stage-advance leg (default OFF = INERT). Best-effort and
        # no-throw: a stage-advance failure NEVER fails the receipt (the comment
        # already succeeded). See _advance_stage.
        await self._advance_stage(company_id, kind)
        return ReceiptPostResponse(
            business_gid=business_gid,
            story_gid=story.gid,
            outcome="posted",
        )

    # ------------------------------------------------------------------
    # Forwarding-Stage write leg (config-gated, best-effort, no-throw).
    # ------------------------------------------------------------------

    async def _advance_stage(self, company_id: str, kind: str) -> None:
        """Advance the Forwarding-Stage field on the clinic's CI task (ADR-FS-004).

        The whole leg is wrapped no-throw: ANY exception is logged and swallowed
        so the receipt's comment outcome always stands (R-2). The dark-posture
        gate short-circuits FIRST: when the write config is not fully active, this
        is a pure NO-OP with ZERO Asana calls -- byte-identical to the comment-only
        baseline (T-W1).
        """
        if not self._stage_cfg.is_active:
            return

        try:
            proposed = RECEIPT_KIND_TO_STAGE.get(kind)
            if proposed is None:  # pragma: no cover -- kind already 422'd upstream
                return

            option_gid = self._stage_cfg.option_gids.get(proposed.value)
            if not option_gid:
                # The target stage has no configured option GID -> cannot PUT.
                # NO-OP (do not guess an option), log for operator visibility.
                logger.info(
                    "forwarding_stage_option_unconfigured",
                    extra={"company_id": company_id, "proposed": proposed.value},
                )
                return

            ci_gid = await self._resolve_ci_task_gid(company_id)
            if ci_gid is None:
                # 0 or >1 CI matches -> best-effort skip (never guess a receiver).
                return

            current = await self._read_current_stage(ci_gid)
            decision = self._stage_validator.evaluate(current, proposed)  # type: ignore[arg-type]

            if decision.is_refusal:
                # LOUD: the machine tried to regress or read an unknown option.
                logger.warning(
                    decision.outcome.value,  # stage_regression_refused | stage_unknown_refused
                    extra={
                        "company_id": company_id,
                        "ci_gid": ci_gid,
                        "current": _stage_display(current),
                        "proposed": proposed.value,
                        "reason": decision.reason,
                    },
                )
                return

            if not decision.should_write:
                # NO-OP (idempotent same-stage). Nothing to write.
                logger.info(
                    "forwarding_stage_noop",
                    extra={"company_id": company_id, "ci_gid": ci_gid, "stage": proposed.value},
                )
                return

            await self._client.tasks.update_async(
                ci_gid,
                custom_fields={self._stage_cfg.field_gid: option_gid},
            )
            logger.info(
                "forwarding_stage_advanced",
                extra={
                    "company_id": company_id,
                    "ci_gid": ci_gid,
                    "from_stage": _stage_display(current),
                    "to_stage": proposed.value,
                    "outcome": decision.outcome.value,
                },
            )
        except Exception as exc:
            logger.warning(
                "forwarding_stage_advance_failed",
                extra={"company_id": company_id, "kind": kind, "error": str(exc)},
            )

    async def _resolve_ci_task_gid(self, company_id: str) -> str | None:
        """Resolve ``company_id`` -> the single Calendar Integrations task gid.

        Delegates to the extracted :func:`ci_task_resolution.resolve_ci_task_gid`
        (behaviour-preserving; the resolver is shared with the S4 backfill so
        neither has to import the other's service). See that function for the
        SECOND-resolution semantics (fail-closed on 0/>1 matches, guest-PAT scope).
        """
        return await _resolve_ci_task_gid_impl(
            self._client,
            company_id,
            company_id_field_gid=self._company_id_field_gid,
        )

    async def _read_current_stage(self, ci_gid: str) -> ForwardingStage | _UnknownStage | None:
        """Read the CI task's current Forwarding-Stage value.

        Delegates to the extracted :func:`ci_task_resolution.read_current_stage`
        (behaviour-preserving). Returns ``None`` (unset), a :class:`ForwardingStage`
        (mapped option), or an :class:`_UnknownStage` sentinel (unmapped option ->
        validator fail-closes).
        """
        return await _read_current_stage_impl(
            self._client,
            ci_gid,
            field_gid=self._stage_cfg.field_gid,
            option_gids=self._stage_cfg.option_gids,
        )
