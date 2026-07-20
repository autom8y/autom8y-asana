"""Forwarding-Stage vocabulary + reconciliation + transition validator (pure).

The operator hand-seeded an Asana single-select "Forwarding Stage" custom field
on the Calendar Integrations project with the target vocabulary
``Sent -> Approved -> Verified -> Stalled -> Flowing -> Live`` plus a surplus
``Inactive``. Independently, the EBI machinery emits a ``ReceiptKind`` StrEnum
consumed by the receipts provider. This module is the codified reconciliation of
those two vocabularies -- the human-onboarding language and the machine
lifecycle-event language -- as an asserted-by-test contract (TDD S1 / ADR-FS-001
.. ADR-FS-005).

Purity contract (Clean-Architecture / DIP): this module depends on NOTHING in
the infrastructure layer -- no ``AsanaClient``, no ``ApiSettings``, no I/O. It
imports only the pure ``ReceiptKind`` enum (itself an ``enum.StrEnum`` with no
I/O). The option-GID <-> stage binding is CONFIG (injected by the service),
never resolved here: the domain defines the vocabulary and the transition rules;
infrastructure supplies the workspace-specific GIDs. Every rule below is a pure
function over ``(current, proposed, rank_table)`` and is exhaustively
unit-testable with no mocks.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ForwardingStage(StrEnum):
    """The canonical Forwarding-Stage vocabulary (7 members).

    The MEMBER SET is code (the vocabulary is a contract the machine and the
    human seam both speak). The enum-value -> Asana option-GID BINDING is config
    (see the service layer), never hardcoded here -- option GIDs are
    workspace artifacts the operator owns.

    Spine order (monotonic-forward): ``Sent -> Approved -> Verified -> Flowing
    -> Live``. ``Stalled`` is an off-spine warning overlay reachable from
    ``Verified``/``Flowing``. ``Inactive`` is a data-driven terminal/parked
    state (disposition config-bound, see ``StageDisposition``) reserved for
    churned/paused clinics and set by a human today; machine-set-Inactive is a
    POLICY switch (default OFF), re-openable by a future ruling WITHOUT code
    change (operator sovereign ruling 2026-07-09).
    """

    SENT = "Sent"  # human affordance: rep marked the forwarding request sent
    APPROVED = "Approved"  # human affordance: Google forwarding approved
    VERIFIED = "Verified"  # machine: vf- link resolved + binding row written
    STALLED = "Stalled"  # machine (off-spine): verified but silent past N hours
    FLOWING = "Flowing"  # machine: first real (non-forwarding) inbound seen
    LIVE = "Live"  # machine: first booking completed end-to-end
    INACTIVE = "Inactive"  # terminal/parked (churned/paused); disposition config-bound


# ---------------------------------------------------------------------------
# Reconciliation: ReceiptKind value (machine) -> ForwardingStage (advances to)
# ---------------------------------------------------------------------------

# The RULED map (ADR-FS-002), derived from the ReceiptKind docstring semantics.
# Keyed by the ReceiptKind STRING VALUE (the lowercase wire value) so the pure
# domain layer stays free of any dependency on the ``api.routes`` layer (DIP: the
# domain points at NOTHING inward; infrastructure/application point at it). The
# reconciliation invariant test (T-M1, test layer) is free to import the real
# ``ReceiptKind`` enum and assert this map is TOTAL over it -- that assertion is
# where the string keys are proven to be exactly the ReceiptKind value set.
#
# The human-set stages Sent/Approved have NO ReceiptKind -- they are rep/operator
# affordances set by hand in the Asana console. The machine NEVER sets or
# regresses them, and nothing maps to Inactive (a de-enrollment is a human act).
RECEIPT_KIND_TO_STAGE: dict[str, ForwardingStage] = {
    "verified": ForwardingStage.VERIFIED,
    "mail_observed": ForwardingStage.FLOWING,
    "first_booking": ForwardingStage.LIVE,
    "nudge": ForwardingStage.STALLED,
}


# ---------------------------------------------------------------------------
# Rank table (monotonic-forward spine) -- config-bound, not magic in comparator
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StageRankTable:
    """Spine ranks for the monotonic-forward comparator (ADR-FS-003).

    The comparator does a ``<``/``>`` on these ranks; keeping them in an injected
    table (rather than magic numbers inside the validator) is the DEFER-carry
    watch from the shape (DEFER-S4-TEETH-COMPARATOR): any comparator edit must
    upgrade the fixture first. ``Stalled`` and ``Inactive`` are OFF the linear
    spine and carry no spine rank -- the validator handles them by branch, not by
    rank comparison.
    """

    #: The linear spine: Sent(0) -> Approved(1) -> Verified(2) -> Flowing(3) -> Live(4).
    spine: tuple[ForwardingStage, ...] = (
        ForwardingStage.SENT,
        ForwardingStage.APPROVED,
        ForwardingStage.VERIFIED,
        ForwardingStage.FLOWING,
        ForwardingStage.LIVE,
    )
    #: The stages from which a ``Stalled`` overlay is a legitimate (non-regressing)
    #: mark: a clinic that is verified/flowing can be flagged stalled without
    #: losing the underlying progress. A ``Live`` clinic is NOT stalled.
    stall_reachable_from: frozenset[ForwardingStage] = frozenset(
        {ForwardingStage.VERIFIED, ForwardingStage.FLOWING}
    )
    #: When a clinic re-advances off ``Stalled`` (next mail_observed/first_booking),
    #: its underlying progress is treated as at least this rank (Verified) so the
    #: forward advance is allowed rather than read as a regression.
    stall_resume_stage: ForwardingStage = ForwardingStage.VERIFIED

    def rank(self, stage: ForwardingStage) -> int | None:
        """Spine rank of ``stage`` (0-based), or ``None`` if off-spine.

        ``Stalled`` and ``Inactive`` are off-spine and return ``None``.
        """
        try:
            return self.spine.index(stage)
        except ValueError:
            return None


class StageDisposition(StrEnum):
    """Data-driven disposition of the surplus ``Inactive`` stage (ADR-FS-005).

    The operator ruling on ``Inactive`` (terminal vs parked vs ignored) is a
    CONFIG value, never a code branch. Defaults are supplied by the service layer
    (safe default: ``PARKED``). Semantics:

    - ``PARKED``  -- machine refuses to auto-advance an ``Inactive`` clinic; a
                     human must re-activate it (the safe default).
    - ``TERMINAL`` -- same refusal, but semantically permanent (churned/paused);
                     equivalent to PARKED for the validator, distinct for the
                     operator's reporting intent.
    - ``IGNORED`` -- the ``Inactive`` value is treated as absent and machine
                     advancement proceeds normally (re-enrollment-in-progress).
    """

    PARKED = "parked"
    TERMINAL = "terminal"
    IGNORED = "ignored"


class TransitionOutcome(StrEnum):
    """The five terminal outcomes of a transition evaluation."""

    ADVANCE = "advance"  # proposed rank > current spine rank; PUT the new stage
    NO_OP = "noop_same_stage"  # proposed == current; idempotent, no write
    STALL_OVERLAY = "stall_overlay"  # legitimate Stalled mark; PUT Stalled
    REFUSE_REGRESSION = "stage_regression_refused"  # spine backward; refuse + count (LOUD)
    REFUSE_UNKNOWN = "stage_unknown_refused"  # unmapped/unknown option; fail-closed


@dataclass(frozen=True)
class TransitionDecision:
    """Result of ``StageTransitionValidator.evaluate``.

    ``should_write`` is the single load-bearing bit the service acts on: only
    ``ADVANCE`` and ``STALL_OVERLAY`` write. ``reason`` carries the human-readable
    rationale for the log line (the LOUD refuse counters key off ``outcome``).
    """

    outcome: TransitionOutcome
    reason: str

    @property
    def should_write(self) -> bool:
        """True iff the resolved CI-task stage field should be PUT."""
        return self.outcome in (TransitionOutcome.ADVANCE, TransitionOutcome.STALL_OVERLAY)

    @property
    def is_refusal(self) -> bool:
        """True for the two fail-closed / LOUD refuse outcomes (metric key)."""
        return self.outcome in (
            TransitionOutcome.REFUSE_REGRESSION,
            TransitionOutcome.REFUSE_UNKNOWN,
        )


class StageTransitionValidator:
    """Pure monotonic-forward transition validator (ADR-FS-003).

    A single-select holds exactly one value; this validator decides whether a
    proposed machine advance is allowed, given the current field value. The
    machine NEVER regresses a spine stage and NEVER guesses on an unknown value
    (fail-closed). The ONLY off-spine legitimate move is a ``Stalled`` overlay
    from ``Verified``/``Flowing``.

    Constructed with an injected ``StageRankTable`` and the ``Inactive``
    disposition (config-bound). No I/O; ``evaluate`` is a pure function.
    """

    def __init__(
        self,
        rank_table: StageRankTable | None = None,
        *,
        inactive_disposition: StageDisposition = StageDisposition.PARKED,
    ) -> None:
        self._ranks = rank_table or StageRankTable()
        self._inactive_disposition = inactive_disposition

    def evaluate(
        self,
        current: ForwardingStage | None,
        proposed: ForwardingStage,
    ) -> TransitionDecision:
        """Decide the transition ``current -> proposed``.

        Args:
            current: the CI task's present Forwarding-Stage value, or ``None`` if
                the field is unset/empty (a fresh clinic). A ``None`` current is a
                clean advance from below the spine floor.
            proposed: the stage the machine wants to advance to (already resolved
                from ``RECEIPT_KIND_TO_STAGE``; always one of the four machine
                targets ``{Verified, Flowing, Live, Stalled}``).

        Returns:
            A :class:`TransitionDecision`. Rule order (ADR-FS-003):
              1. REFUSE-UNKNOWN  -- proposed not a member / current an unknown value
              2. Inactive-disposition guard (parked/terminal refuse; ignored proceeds)
              3. NO-OP           -- proposed == current
              4. STALL-OVERLAY / Stalled-refusal branch
              5. ADVANCE vs REFUSE-REGRESSION on the spine
        """
        # 1. Fail-CLOSED on an unknown proposed stage (never guess). ``proposed``
        #    is typed as ForwardingStage, but a caller may pass a value coerced
        #    from an untrusted option-GID read; guard defensively.
        if not isinstance(proposed, ForwardingStage):
            return TransitionDecision(
                TransitionOutcome.REFUSE_UNKNOWN,
                f"proposed stage {proposed!r} is not a ForwardingStage member",
            )

        # ``current`` may be an unknown option GID that the service could not map
        # to a ForwardingStage -- it passes ``None`` for unset, but passes a
        # SENTINEL-free unknown as itself only if it is a member. A non-member,
        # non-None current is fail-closed unknown.
        if current is not None and not isinstance(current, ForwardingStage):
            return TransitionDecision(
                TransitionOutcome.REFUSE_UNKNOWN,
                f"current stage {current!r} is an unknown/unmapped option; refusing",
            )

        # 2. Inactive-disposition guard: a de-enrolled/parked clinic is not
        #    auto-advanced by the machine unless the operator ruling flips the
        #    disposition to IGNORED (a config change, never code -- ADR-FS-005).
        if current == ForwardingStage.INACTIVE:
            if self._inactive_disposition is StageDisposition.IGNORED:
                # Treat Inactive as absent: advancement proceeds as if from None.
                return self._evaluate_spine(None, proposed)
            return TransitionDecision(
                TransitionOutcome.REFUSE_REGRESSION,
                f"clinic is Inactive (disposition={self._inactive_disposition.value}); "
                f"machine refuses to auto-advance a parked/terminal clinic",
            )

        # A machine advance never TARGETS Inactive (nothing maps to it); guard.
        if proposed == ForwardingStage.INACTIVE:
            return TransitionDecision(
                TransitionOutcome.REFUSE_UNKNOWN,
                "machine never sets Inactive (human-only de-enrollment); refusing",
            )

        # 3. Idempotent NO-OP: proposed == current -> allowed, no write.
        if current == proposed:
            return TransitionDecision(
                TransitionOutcome.NO_OP,
                f"already at {proposed.value}; idempotent no-op",
            )

        # 4. Stalled overlay branch (off-spine).
        if proposed == ForwardingStage.STALLED:
            return self._evaluate_stall(current)

        # 5. Spine advance / regression.
        return self._evaluate_spine(current, proposed)

    def _evaluate_stall(self, current: ForwardingStage | None) -> TransitionDecision:
        """A ``Stalled`` overlay is legitimate only from Verified/Flowing.

        From ``Live`` a nudge is REFUSED (a booking clinic is not stalled -- this
        protects against a spurious nudge on an already-live clinic). From a
        pre-Verified stage (Sent/Approved/None) a stall is a regression-shaped
        surprise the machine also refuses (the clinic was never verified, so a
        stall signal is incoherent).
        """
        if current in self._ranks.stall_reachable_from:
            return TransitionDecision(
                TransitionOutcome.STALL_OVERLAY,
                f"stall overlay from {current.value if current else None}; "
                f"underlying progress preserved (resume at "
                f"{self._ranks.stall_resume_stage.value})",
            )
        if current == ForwardingStage.LIVE:
            return TransitionDecision(
                TransitionOutcome.REFUSE_REGRESSION,
                "a Live (booking) clinic is not stalled; refusing the nudge overlay",
            )
        # Remaining currents: Sent, Approved, None, Stalled -- pre-verified or
        # already-stalled; a stall overlay from here is incoherent, so refuse.
        return TransitionDecision(
            TransitionOutcome.REFUSE_REGRESSION,
            f"stall overlay not reachable from {current.value if current else None} "
            f"(clinic not yet verified); refusing",
        )

    def _evaluate_spine(
        self,
        current: ForwardingStage | None,
        proposed: ForwardingStage,
    ) -> TransitionDecision:
        """Monotonic-forward comparison on the spine (ADVANCE vs REFUSE-REGRESSION).

        A ``current`` that is off-spine (``Stalled``) resumes at the configured
        ``stall_resume_stage`` rank so the forward advance is allowed rather than
        read as a regression.
        """
        proposed_rank = self._ranks.rank(proposed)
        if proposed_rank is None:  # pragma: no cover -- Stalled handled upstream
            return TransitionDecision(
                TransitionOutcome.REFUSE_UNKNOWN,
                f"proposed {proposed.value} has no spine rank; refusing",
            )

        if current is None:
            # Fresh clinic (no stage) -> any spine advance is allowed.
            return TransitionDecision(
                TransitionOutcome.ADVANCE,
                f"advance from unset to {proposed.value}",
            )

        if current == ForwardingStage.STALLED:
            current_rank: int | None = self._ranks.rank(self._ranks.stall_resume_stage)
        else:
            current_rank = self._ranks.rank(current)

        if current_rank is None:  # pragma: no cover -- unknowns handled upstream
            return TransitionDecision(
                TransitionOutcome.REFUSE_UNKNOWN,
                f"current {current.value} has no spine rank; refusing",
            )

        if proposed_rank > current_rank:
            return TransitionDecision(
                TransitionOutcome.ADVANCE,
                f"advance {current.value}({current_rank}) -> {proposed.value}({proposed_rank})",
            )
        # proposed_rank <= current_rank (== handled as NO-OP upstream; here it is <)
        return TransitionDecision(
            TransitionOutcome.REFUSE_REGRESSION,
            f"machine refuses regression {current.value}({current_rank}) -> "
            f"{proposed.value}({proposed_rank})",
        )


__all__ = [
    "RECEIPT_KIND_TO_STAGE",
    "ForwardingStage",
    "StageDisposition",
    "StageRankTable",
    "StageTransitionValidator",
    "TransitionDecision",
    "TransitionOutcome",
]
