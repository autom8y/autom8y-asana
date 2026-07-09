"""Forwarding-Stage backfill orchestrator: gather -> derive -> resolve ->
validate -> plan/apply.

The load-bearing shape (§2 crux): the backfill derives a ``proposed`` stage
DIRECTLY from monolith log evidence (the ONE new pure function
``derive_stage``), then feeds it through the UNCHANGED S1
:class:`StageTransitionValidator`. Everything downstream of ``proposed`` -- the
monotonic guard, never-downgrade, fail-closed-on-unknown, NO-OP idempotence --
is reused byte-for-byte from S1. The backfill adds ZERO new transition logic.

Two modes:
  - ``plan`` (default / dry-run): gather, derive, resolve, validate, emit a PLAN
    artifact. ZERO Asana writes.
  - ``apply``: same, but for every ``action=stamp`` row PUT the custom field and
    emit a per-task receipt. Gated on the S1 write config (``is_active``); an
    inactive-config apply REFUSES loudly (never a silent no-op in apply mode).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.automation.forwarding_stage_backfill.evidence_source import (
    MonolithEvidenceSource,
    assert_not_capped,
)
from autom8_asana.domain.forwarding_stage import (
    ForwardingStage,
    StageDisposition,
    StageRankTable,
    StageTransitionValidator,
    TransitionOutcome,
)
from autom8_asana.domain.forwarding_stage_backfill import ClinicEvidence, derive_stage
from autom8_asana.services.ci_task_resolution import (
    UnknownStage,
    read_current_stage,
    resolve_ci_task_gid,
)

if TYPE_CHECKING:
    from autom8_asana import AsanaClient

logger = get_logger(__name__)


class BackfillMode(StrEnum):
    """The two backfill postures."""

    PLAN = "plan"  # dry-run DEFAULT: preview only, ZERO writes
    APPLY = "apply"  # stamp the board, per-task receipts, idempotent


class BackfillAction(StrEnum):
    """The per-clinic action a PLAN row records (what would/did happen)."""

    STAMP = "stamp"  # ADVANCE / STALL_OVERLAY -> a PUT (apply) or would-PUT (plan)
    SKIP = "skip"  # no derivable stage (no_evidence) -> NO STAMP (honest absence)
    UNRESOLVED = "unresolved"  # 0 or >1 CI task matches -> operator triage bucket
    NOOP = "noop"  # already at the derived stage -> idempotent, no write
    REFUSE = "refuse"  # regression / unknown-current -> LOUD, counted, no write


@dataclass(frozen=True)
class BackfillWriteConfig:
    """The write leg's config (reuses the S1 ``ForwardingStageWriteConfig`` shape).

    Kept as a plain dataclass here (not imported from ``receipts_service``) so the
    orchestrator does NOT pull in the receipts route / its circular-import
    surface. The CLI builds this from the S1 ``ApiSettings.forwarding_stage_*``
    fields; ``is_active`` is the SAME three-gate predicate as S1.
    """

    enabled: bool = False
    field_gid: str = ""
    option_gids: dict[str, str] = field(default_factory=dict)
    inactive_disposition: StageDisposition = StageDisposition.PARKED

    @property
    def is_active(self) -> bool:
        """True iff the write leg is fully configured (enabled + field + options)."""
        return bool(self.enabled and self.field_gid and self.option_gids)


class BackfillWriteConfigInactive(RuntimeError):
    """``apply`` was invoked but the S1 write config is not active.

    The operator explicitly asked to WRITE; a silent no-op would hide that the
    switch is off. This names the exact missing setting and exits non-zero
    (DD-5 / T-C2). Never fires in ``plan`` mode (plan can preview pre-flip).
    """

    def __init__(self, cfg: BackfillWriteConfig) -> None:
        missing = []
        if not cfg.enabled:
            missing.append("forwarding_stage_write_enabled=false")
        if not cfg.field_gid:
            missing.append("forwarding_stage_field_gid is empty")
        if not cfg.option_gids:
            missing.append("forwarding_stage_option_gids is empty")
        self.missing = missing
        super().__init__(
            "apply mode requires the S1 Forwarding-Stage write config to be "
            f"active, but: {'; '.join(missing) or 'unknown gap'}. Refusing to "
            "run apply as a silent no-op (the operator asked to write). Populate "
            "the ASANA_API_FORWARDING_STAGE_* settings and re-run."
        )


@dataclass
class ClinicPlanRow:
    """One clinic's line in the PLAN (and, under apply, its outcome)."""

    inbox_uuid: str
    ci_task_gid: str | None
    booking_mail_count: int
    booking_mail_last_seen: str | None
    forwarding_confirmation_seen: bool
    forwarding_confirmation_at: str | None
    derived_stage: str | None
    current_stage: str | None
    decision_outcome: str | None
    action: str
    reason: str | None = None
    #: Populated under apply for a stamped row (the per-task receipt).
    asana_response_status: str | None = None


@dataclass
class DenominatorHeader:
    """The PLAN header's denominator block (DD-2 / G-DENOM).

    ``distinct_clinics_observed`` is the TRUE denominator (never the 60-row
    triage floor). ``cap_hit`` is always False in an emitted PLAN -- a capped run
    ABORTS before this is built.
    """

    window_days: int
    distinct_clinics_observed: int
    booking_mail_total: int
    booking_clinics: int
    confirmation_clinics: int
    query_row_cap: int
    booking_row_count: int
    confirmation_row_count: int
    cap_hit: bool
    malformed_booking_records: int
    malformed_confirmation_records: int
    generated_at: str


@dataclass
class BackfillPlan:
    """The full PLAN artifact: denominator header + per-clinic rows + counts."""

    mode: str
    header: DenominatorHeader
    rows: list[ClinicPlanRow]
    unresolved: list[ClinicPlanRow]
    counts: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        """JSON-serializable form for the artifact file."""
        return {
            "mode": self.mode,
            "header": asdict(self.header),
            "counts": self.counts,
            "rows": [asdict(r) for r in self.rows],
            "unresolved": [asdict(r) for r in self.unresolved],
        }


class ForwardingStageBackfill:
    """Orchestrates one backfill run (plan or apply).

    Depends on the :class:`MonolithEvidenceSource` port (fake-able), an
    :class:`AsanaClient` (for the CI-task resolution + the apply PUT), the S1
    validator (unchanged), and the write config. No global state.
    """

    def __init__(
        self,
        *,
        evidence_source: MonolithEvidenceSource,
        client: AsanaClient,
        company_id_field_gid: str,
        write_config: BackfillWriteConfig,
        nudge_threshold_hours: int = 48,
    ) -> None:
        self._evidence = evidence_source
        self._client = client
        self._company_id_field_gid = company_id_field_gid
        self._cfg = write_config
        self._nudge_h = nudge_threshold_hours
        self._validator = StageTransitionValidator(
            StageRankTable(),
            inactive_disposition=write_config.inactive_disposition,
        )

    async def run(self, *, mode: BackfillMode, window_days: int) -> BackfillPlan:
        """Execute the backfill. See module docstring for the sequence."""
        # ── apply-mode config gate (top; DD-5 / T-C2) ──────────────────────
        if mode is BackfillMode.APPLY and not self._cfg.is_active:
            raise BackfillWriteConfigInactive(self._cfg)

        now = datetime.now(UTC)

        # ── 1. GATHER (infra port) + denominator guard (DD-2 / T-B5) ───────
        booking = self._evidence.booking_mail_counts(window_days)
        assert_not_capped(booking, kind="booking_mail")
        confirms = self._evidence.forwarding_confirmations(window_days)
        assert_not_capped(confirms, kind="forwarding_confirmation")

        # The observed denominator: union of inbox uuids across both signals.
        clinics = sorted(set(booking.signals) | set(confirms.signals))

        rows: list[ClinicPlanRow] = []
        unresolved: list[ClinicPlanRow] = []

        for inbox in clinics:
            b = booking.signals.get(inbox)
            c = confirms.signals.get(inbox)
            evidence = ClinicEvidence(inbox_uuid=inbox, booking=b, confirmation=c)

            # ── 2. DERIVE (pure domain; no I/O) ───────────────────────────
            proposed = derive_stage(evidence, now, nudge_threshold_hours=self._nudge_h)

            row = ClinicPlanRow(
                inbox_uuid=inbox,
                ci_task_gid=None,
                booking_mail_count=(b.count if b else 0),
                booking_mail_last_seen=(b.last_seen.isoformat() if b else None),
                forwarding_confirmation_seen=(c is not None),
                forwarding_confirmation_at=(c.confirmed_at.isoformat() if c else None),
                derived_stage=(proposed.value if proposed else None),
                current_stage=None,
                decision_outcome=None,
                action=BackfillAction.SKIP.value,
            )

            if proposed is None:
                # NO STAMP -- honest absence (G-DENOM; T-D4/T-B: no evidence).
                row.action = BackfillAction.SKIP.value
                row.reason = "no_evidence"
                rows.append(row)
                continue

            # ── 3. RESOLVE (reused S1 idiom; UNRESOLVED never guessed) ─────
            ci_gid = await resolve_ci_task_gid(
                self._client,
                inbox,
                company_id_field_gid=self._company_id_field_gid,
            )
            if ci_gid is None:
                # 0 or >1 CI matches -> UNRESOLVED bucket (DD-3 / T-B4). The
                # malformed/truncated-inbox class: NEVER guess a clinic.
                row.action = BackfillAction.UNRESOLVED.value
                row.reason = "unresolved_no_ci_task_or_ambiguous"
                unresolved.append(row)
                continue
            row.ci_task_gid = ci_gid

            # ── 4. VALIDATE (reused S1 validator; never-downgrade) ─────────
            current = await read_current_stage(
                self._client,
                ci_gid,
                field_gid=self._cfg.field_gid,
                option_gids=self._cfg.option_gids,
            )
            row.current_stage = _stage_display(current)
            decision = self._validator.evaluate(_validator_current(current), proposed)
            row.decision_outcome = decision.outcome.value

            if decision.outcome in (
                TransitionOutcome.ADVANCE,
                TransitionOutcome.STALL_OVERLAY,
            ):
                row.action = BackfillAction.STAMP.value
                if mode is BackfillMode.APPLY:
                    await self._stamp(row, proposed)
            elif decision.outcome is TransitionOutcome.NO_OP:
                row.action = BackfillAction.NOOP.value
                row.reason = "already_at_stage"
            else:  # REFUSE_REGRESSION | REFUSE_UNKNOWN
                row.action = BackfillAction.REFUSE.value
                row.reason = decision.reason
                logger.warning(
                    decision.outcome.value,
                    extra={
                        "inbox": inbox,
                        "ci_gid": ci_gid,
                        "current": row.current_stage,
                        "proposed": proposed.value,
                        "reason": decision.reason,
                    },
                )

            rows.append(row)

        header = DenominatorHeader(
            window_days=window_days,
            distinct_clinics_observed=len(clinics),
            booking_mail_total=booking.booking_mail_total,
            booking_clinics=len(booking.signals),
            confirmation_clinics=len(confirms.signals),
            query_row_cap=_evidence_row_cap(self._evidence),
            booking_row_count=booking.row_count,
            confirmation_row_count=confirms.row_count,
            cap_hit=False,  # a capped run aborts before here
            malformed_booking_records=booking.malformed_records,
            malformed_confirmation_records=confirms.malformed_records,
            generated_at=now.isoformat(),
        )

        counts = _count_actions(rows, unresolved)
        return BackfillPlan(
            mode=mode.value,
            header=header,
            rows=rows,
            unresolved=unresolved,
            counts=counts,
        )

    async def _stamp(self, row: ClinicPlanRow, proposed: ForwardingStage) -> None:
        """PUT the derived stage on the CI task and record the per-task receipt.

        Only called in apply mode for a should-write decision, AFTER the CI task
        resolved (so ``row.ci_task_gid`` is non-None). ``option_gids`` is
        guaranteed populated (is_active gate) and contains ``proposed`` (derived
        stages are always in the config map for a machine target).
        """
        ci_gid = row.ci_task_gid
        if ci_gid is None:  # pragma: no cover -- only reached with a resolved gid
            return
        option_gid = self._cfg.option_gids.get(proposed.value)
        if not option_gid:
            # Defensive: a derived stage with no configured option GID cannot be
            # PUT. Downgrade to a skip-with-reason rather than guess.
            row.action = BackfillAction.SKIP.value
            row.reason = f"no_option_gid_for_{proposed.value}"
            logger.info(
                "backfill_stamp_option_unconfigured",
                extra={"inbox": row.inbox_uuid, "proposed": proposed.value},
            )
            return
        await self._client.tasks.update_async(
            ci_gid,
            custom_fields={self._cfg.field_gid: option_gid},
        )
        row.asana_response_status = "ok"
        logger.info(
            "backfill_forwarding_stage_stamped",
            extra={
                "inbox": row.inbox_uuid,
                "ci_gid": row.ci_task_gid,
                "from_stage": row.current_stage,
                "to_stage": proposed.value,
                "outcome": row.decision_outcome,
            },
        )


def _evidence_row_cap(evidence: MonolithEvidenceSource) -> int:
    """Best-effort read of the evidence source's configured row cap (for the
    PLAN header). Falls back to 0 when the source exposes no config (fake)."""
    cfg = getattr(evidence, "_config", None)
    return getattr(cfg, "query_row_cap", 0) if cfg is not None else 0


def _validator_current(
    current: ForwardingStage | UnknownStage | None,
) -> ForwardingStage | None:
    """Coerce the read current stage for the validator.

    A mapped :class:`ForwardingStage` or ``None`` passes through; an
    :class:`UnknownStage` sentinel is passed through as-is so the validator's
    ``isinstance(current, ForwardingStage)`` guard fail-CLOSES (REFUSE_UNKNOWN).
    The validator accepts ``current`` as ``ForwardingStage | None`` in its type
    hints but defensively guards non-members -- so passing the sentinel through
    is exactly the S1 fail-closed contract.
    """
    if current is None or isinstance(current, ForwardingStage):
        return current
    return current  # type: ignore[return-value]  # sentinel -> validator fail-closes


def _stage_display(current: ForwardingStage | UnknownStage | None) -> str | None:
    """Log/PLAN-safe rendering of a read current stage (handles the sentinel)."""
    if current is None:
        return None
    if isinstance(current, ForwardingStage):
        return current.value
    return f"unknown:{current.option_gid}"


def _count_actions(rows: list[ClinicPlanRow], unresolved: list[ClinicPlanRow]) -> dict[str, int]:
    """Tally per-action counts + the per-stage stamp breakdown for the summary."""
    counts: dict[str, int] = {
        "stamp": 0,
        "stamp_Flowing": 0,
        "stamp_Stalled": 0,
        "stamp_Verified": 0,
        "skip": 0,
        "noop": 0,
        "refuse": 0,
        "unresolved": len(unresolved),
    }
    for r in rows:
        counts[r.action] = counts.get(r.action, 0) + 1
        if r.action == BackfillAction.STAMP.value and r.derived_stage:
            key = f"stamp_{r.derived_stage}"
            counts[key] = counts.get(key, 0) + 1
    return counts


__all__ = [
    "BackfillAction",
    "BackfillMode",
    "BackfillPlan",
    "BackfillWriteConfig",
    "BackfillWriteConfigInactive",
    "ClinicPlanRow",
    "DenominatorHeader",
    "ForwardingStageBackfill",
]
