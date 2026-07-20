"""Two-sided discriminating tests for the Forwarding-Stage domain (TDD S1 §7).

Pure-domain tests: no client, no config-object, no mocks. Every guard is proven
RED-on-the-defect AND GREEN-without-it (G-THEATER discipline). The load-bearing
teeth:

  - T-M1 reconciliation TOTAL + human/machine-disjoint (nothing maps to
    Sent/Approved/Inactive; every ReceiptKind maps into the lattice).
  - T-M3 machine NEVER regresses (Live->Sent/Verified REFUSED + counted).
  - T-M4 Stalled overlay two-sided (Verified->Stalled OK; Live->Stalled REFUSED).
  - T-M5 unknown fails CLOSED (never guess an unmapped option).
  - T-M6 idempotent NO-OP (re-apply same stage -> no write).
  - T-M7 Inactive disposition is data-driven (parked refuses; ignored proceeds)
    with ZERO code branch difference -- only the injected config differs.

Each test names the RED side (the defect a wrong impl would exhibit) in its
docstring so the discrimination is legible, per the #980 mutation-matrix house
standard.
"""

from __future__ import annotations

import pytest

from autom8_asana.api.routes.receipts_models import ReceiptKind
from autom8_asana.domain.forwarding_stage import (
    RECEIPT_KIND_TO_STAGE,
    ForwardingStage,
    StageDisposition,
    StageRankTable,
    StageTransitionValidator,
    TransitionOutcome,
)

# The three stages the machine must NEVER set (human affordances + de-enrollment).
_HUMAN_ONLY_OR_TERMINAL = {
    ForwardingStage.SENT,
    ForwardingStage.APPROVED,
    ForwardingStage.INACTIVE,
}

# The four machine targets the reconciliation image must equal.
_MACHINE_TARGETS = {
    ForwardingStage.VERIFIED,
    ForwardingStage.FLOWING,
    ForwardingStage.LIVE,
    ForwardingStage.STALLED,
}


def _validator(*, inactive: StageDisposition = StageDisposition.PARKED) -> StageTransitionValidator:
    """A validator with the default rank table and a chosen Inactive disposition."""
    return StageTransitionValidator(StageRankTable(), inactive_disposition=inactive)


# ---------------------------------------------------------------------------
# T-M1 -- Reconciliation table is TOTAL + human/machine-disjoint
# ---------------------------------------------------------------------------


class TestReconciliationTable:
    def test_m1_total_over_receipt_kind(self) -> None:
        """T-M1a: every ReceiptKind VALUE is a key in the map (TOTAL).

        The map is keyed by the ReceiptKind wire value (string) so the pure
        domain stays DIP-clean (no api.routes dependency). This test -- in the
        test layer, free to import the real enum -- proves the string keys are
        EXACTLY the ReceiptKind value set.

        RED side: a ReceiptKind missing from RECEIPT_KIND_TO_STAGE (e.g. a new
        EBI kind shipped without a provider update) would leave a gap here -- the
        set-equality FAILS. This is the reconciliation invariant that makes S1's
        exit-criterion 'asserted by a test, not prose'.
        """
        assert set(RECEIPT_KIND_TO_STAGE.keys()) == {k.value for k in ReceiptKind}

    def test_m1_image_is_exactly_the_machine_targets(self) -> None:
        """T-M1b: the map's IMAGE equals {Verified, Flowing, Live, Stalled}.

        RED side: a map entry pointing at Sent/Approved/Inactive would put a
        forbidden stage into the image -- disjointness FAILS.
        """
        image = set(RECEIPT_KIND_TO_STAGE.values())
        assert image == _MACHINE_TARGETS

    def test_m1_nothing_maps_to_human_or_terminal(self) -> None:
        """T-M1c: no ReceiptKind maps to Sent/Approved/Inactive (disjointness).

        RED side: nudge->Inactive, or verified->Approved, would trip this. The
        machine owns Verified->Flowing->Live (+Stalled); the human owns
        Sent->Approved; nothing machine-set is Inactive.
        """
        for kind, stage in RECEIPT_KIND_TO_STAGE.items():
            assert stage not in _HUMAN_ONLY_OR_TERMINAL, f"{kind} -> {stage} is forbidden"

    def test_m1_every_image_member_is_a_forwarding_stage(self) -> None:
        """T-M1d: every mapped value is a real ForwardingStage member."""
        for stage in RECEIPT_KIND_TO_STAGE.values():
            assert isinstance(stage, ForwardingStage)

    def test_m1_ruled_map_exact_values(self) -> None:
        """T-M1e: the RULED map is exactly the ADR-FS-002 table (pin the ruling).

        RED side: any single mis-mapping (e.g. mail_observed->Live instead of
        Flowing) would break this. Pins the operator-ruled reconciliation so a
        future refactor cannot silently drift it. Keyed by the ReceiptKind value
        strings to keep the domain DIP-clean.
        """
        assert {
            ReceiptKind.VERIFIED.value: ForwardingStage.VERIFIED,
            ReceiptKind.MAIL_OBSERVED.value: ForwardingStage.FLOWING,
            ReceiptKind.FIRST_BOOKING.value: ForwardingStage.LIVE,
            ReceiptKind.NUDGE.value: ForwardingStage.STALLED,
        } == RECEIPT_KIND_TO_STAGE


# ---------------------------------------------------------------------------
# T-M2 -- Correct forward advance GREEN
# ---------------------------------------------------------------------------


class TestForwardAdvance:
    @pytest.mark.parametrize(
        ("current", "proposed"),
        [
            (ForwardingStage.APPROVED, ForwardingStage.VERIFIED),
            (ForwardingStage.VERIFIED, ForwardingStage.FLOWING),
            (ForwardingStage.FLOWING, ForwardingStage.LIVE),
            (ForwardingStage.SENT, ForwardingStage.VERIFIED),  # skips are forward too
        ],
    )
    def test_m2_forward_advance_is_allowed(
        self, current: ForwardingStage, proposed: ForwardingStage
    ) -> None:
        """T-M2: a strictly-forward spine move is ADVANCE (and writes)."""
        decision = _validator().evaluate(current, proposed)
        assert decision.outcome is TransitionOutcome.ADVANCE
        assert decision.should_write is True

    def test_m2_advance_from_unset_field(self) -> None:
        """T-M2b: a fresh clinic (current=None) advances cleanly to any spine stage."""
        decision = _validator().evaluate(None, ForwardingStage.VERIFIED)
        assert decision.outcome is TransitionOutcome.ADVANCE
        assert decision.should_write is True


# ---------------------------------------------------------------------------
# T-M3 -- Regression REFUSED + counted (the headline teeth)
# ---------------------------------------------------------------------------


class TestRegressionRefused:
    @pytest.mark.parametrize(
        ("current", "proposed"),
        [
            (ForwardingStage.LIVE, ForwardingStage.SENT),
            (ForwardingStage.LIVE, ForwardingStage.VERIFIED),
            (ForwardingStage.LIVE, ForwardingStage.FLOWING),
            (ForwardingStage.FLOWING, ForwardingStage.VERIFIED),
            (ForwardingStage.VERIFIED, ForwardingStage.APPROVED),
        ],
    )
    def test_m3_machine_never_regresses(
        self, current: ForwardingStage, proposed: ForwardingStage
    ) -> None:
        """T-M3: a backward spine move is REFUSE_REGRESSION, no write.

        RED side: an impl that returned ADVANCE for evaluate(Live, Sent) -- i.e.
        one that did not compare ranks, or compared them the wrong way -- would
        FAIL here. This is the machine-never-regresses guarantee: a late
        'verified' receipt on an already-Live clinic must not drag the board
        backward. The refusal is LOUD (is_refusal True -> counter key).
        """
        decision = _validator().evaluate(current, proposed)
        assert decision.outcome is TransitionOutcome.REFUSE_REGRESSION
        assert decision.should_write is False
        assert decision.is_refusal is True

    def test_m3_refusal_carries_reason(self) -> None:
        """T-M3b: the refusal names both stages (for the LOUD log line)."""
        decision = _validator().evaluate(ForwardingStage.LIVE, ForwardingStage.SENT)
        assert "Live" in decision.reason and "Sent" in decision.reason


# ---------------------------------------------------------------------------
# T-M4 -- Stalled overlay two-sided
# ---------------------------------------------------------------------------


class TestStallOverlay:
    @pytest.mark.parametrize("current", [ForwardingStage.VERIFIED, ForwardingStage.FLOWING])
    def test_m4_stall_from_verified_or_flowing_allowed(self, current: ForwardingStage) -> None:
        """T-M4a GREEN: Stalled from Verified/Flowing is a legitimate overlay."""
        decision = _validator().evaluate(current, ForwardingStage.STALLED)
        assert decision.outcome is TransitionOutcome.STALL_OVERLAY
        assert decision.should_write is True

    def test_m4_stall_from_live_refused(self) -> None:
        """T-M4b RED-side: Stalled from Live is REFUSED (a booking clinic is live).

        RED side: an impl that let evaluate(Live, Stalled) return STALL_OVERLAY
        would FAIL -- a spurious nudge on a clinic that is already booking must
        not overwrite Live with Stalled.
        """
        decision = _validator().evaluate(ForwardingStage.LIVE, ForwardingStage.STALLED)
        assert decision.outcome is TransitionOutcome.REFUSE_REGRESSION
        assert decision.should_write is False

    @pytest.mark.parametrize("current", [ForwardingStage.SENT, ForwardingStage.APPROVED, None])
    def test_m4_stall_before_verified_refused(self, current: ForwardingStage | None) -> None:
        """T-M4c: Stalled before the clinic was ever Verified is incoherent -> refuse."""
        decision = _validator().evaluate(current, ForwardingStage.STALLED)
        assert decision.outcome is TransitionOutcome.REFUSE_REGRESSION
        assert decision.should_write is False

    def test_m4_readvance_off_stalled_is_allowed(self) -> None:
        """T-M4d: a clinic marked Stalled re-advances forward on the next receipt.

        Stalled's resume rank is Verified(2), so Stalled->Flowing and
        Stalled->Live are ADVANCE (progress preserved, not read as regression),
        while Stalled->Verified is a NO-OP-shaped resume (== resume rank => not a
        forward move => REFUSE_REGRESSION, correctly: re-verifying a stalled
        clinic is not forward progress).
        """
        assert (
            _validator().evaluate(ForwardingStage.STALLED, ForwardingStage.FLOWING).outcome
            is TransitionOutcome.ADVANCE
        )
        assert (
            _validator().evaluate(ForwardingStage.STALLED, ForwardingStage.LIVE).outcome
            is TransitionOutcome.ADVANCE
        )


# ---------------------------------------------------------------------------
# T-M5 -- Unknown fails CLOSED
# ---------------------------------------------------------------------------


class TestUnknownFailsClosed:
    def test_m5_unknown_current_refused(self) -> None:
        """T-M5a: a current value that is not a ForwardingStage -> REFUSE_UNKNOWN.

        Models the service reading an option GID it cannot map to a stage. The
        machine must NOT guess ADVANCE off a garbage current value.

        RED side: an impl that treated an unknown current as None (and thus
        advanced) would FAIL -- that is the fail-OPEN mistake this guard exists
        to prevent.
        """
        decision = _validator().evaluate("garbage-option-gid", ForwardingStage.VERIFIED)  # type: ignore[arg-type]
        assert decision.outcome is TransitionOutcome.REFUSE_UNKNOWN
        assert decision.should_write is False
        assert decision.is_refusal is True

    def test_m5_unknown_proposed_refused(self) -> None:
        """T-M5b: a proposed value that is not a ForwardingStage -> REFUSE_UNKNOWN."""
        decision = _validator().evaluate(ForwardingStage.VERIFIED, "not-a-stage")  # type: ignore[arg-type]
        assert decision.outcome is TransitionOutcome.REFUSE_UNKNOWN
        assert decision.should_write is False

    def test_m5_machine_never_targets_inactive(self) -> None:
        """T-M5c: proposed=Inactive is refused (machine never de-enrolls)."""
        decision = _validator().evaluate(ForwardingStage.VERIFIED, ForwardingStage.INACTIVE)
        assert decision.outcome is TransitionOutcome.REFUSE_UNKNOWN
        assert decision.should_write is False


# ---------------------------------------------------------------------------
# T-M6 -- Idempotent NO-OP
# ---------------------------------------------------------------------------


class TestIdempotentNoOp:
    @pytest.mark.parametrize(
        "stage",
        [
            ForwardingStage.VERIFIED,
            ForwardingStage.FLOWING,
            ForwardingStage.LIVE,
        ],
    )
    def test_m6_same_stage_is_noop(self, stage: ForwardingStage) -> None:
        """T-M6: proposed == current -> NO_OP, no write (idempotent re-post).

        RED side: an impl that PUT on every receipt (no current-read guard) would
        return ADVANCE here and double-write -- FAIL. The idempotent NO-OP is
        what makes a re-delivered receipt a no-op advance (T-W3 at the route).
        """
        decision = _validator().evaluate(stage, stage)
        assert decision.outcome is TransitionOutcome.NO_OP
        assert decision.should_write is False


# ---------------------------------------------------------------------------
# T-M7 -- Inactive disposition is DATA-DRIVEN (config, not code)
# ---------------------------------------------------------------------------


class TestInactiveDisposition:
    def test_m7_parked_refuses_auto_advance(self) -> None:
        """T-M7a: disposition=parked -> machine refuses to advance off Inactive.

        The safe default: a de-enrolled clinic stays parked until a human moves
        it. The refusal is a regression-class refuse (no write).
        """
        decision = _validator(inactive=StageDisposition.PARKED).evaluate(
            ForwardingStage.INACTIVE, ForwardingStage.VERIFIED
        )
        assert decision.outcome is TransitionOutcome.REFUSE_REGRESSION
        assert decision.should_write is False

    def test_m7_terminal_also_refuses(self) -> None:
        """T-M7b: disposition=terminal -> same refusal (semantically permanent)."""
        decision = _validator(inactive=StageDisposition.TERMINAL).evaluate(
            ForwardingStage.INACTIVE, ForwardingStage.LIVE
        )
        assert decision.outcome is TransitionOutcome.REFUSE_REGRESSION
        assert decision.should_write is False

    def test_m7_ignored_proceeds(self) -> None:
        """T-M7c: disposition=ignored -> Inactive treated as absent; advance proceeds.

        The DATA-DRIVEN teeth: the SAME code, given a DIFFERENT injected config
        value, produces the OPPOSITE outcome. There is NO code branch keyed on a
        hardcoded ruling -- the operator ruling on Inactive is exactly a
        one-line config edit (ADR-FS-005 / operator sovereign ruling 2026-07-09).
        """
        decision = _validator(inactive=StageDisposition.IGNORED).evaluate(
            ForwardingStage.INACTIVE, ForwardingStage.VERIFIED
        )
        assert decision.outcome is TransitionOutcome.ADVANCE
        assert decision.should_write is True

    def test_m7_disposition_is_the_only_difference(self) -> None:
        """T-M7d: the outcome flips PURELY on the config value (no code branch).

        Same current, same proposed, same validator class -- ONLY the injected
        StageDisposition differs, and the outcome inverts (REFUSE vs ADVANCE).
        This is the proof that the Inactive ruling is data, not code.
        """
        current, proposed = ForwardingStage.INACTIVE, ForwardingStage.VERIFIED
        parked = _validator(inactive=StageDisposition.PARKED).evaluate(current, proposed)
        ignored = _validator(inactive=StageDisposition.IGNORED).evaluate(current, proposed)
        assert parked.should_write is False
        assert ignored.should_write is True
        assert parked.outcome is not ignored.outcome
