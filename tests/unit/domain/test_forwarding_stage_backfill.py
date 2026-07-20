"""Two-sided discriminating tests for the backfill derivation (TDD S4 §8 T-D*).

Pure-domain tests: no client, no config-object, no AWS, no mocks. Every guard is
proven RED-on-the-defect AND GREEN-without-it (G-THEATER). ``derive_stage`` is
the ONE new pure function S4 adds; its domain is ``{Flowing, Stalled, Verified}``
union ``{None}`` -- NEVER ``Live``.

Each test names the RED side (the defect a wrong impl would exhibit) so the
discrimination is legible.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from autom8_asana.domain.forwarding_stage import ForwardingStage
from autom8_asana.domain.forwarding_stage_backfill import (
    BookingSignal,
    ClinicEvidence,
    ConfirmationSignal,
    derive_stage,
)

NOW = datetime(2026, 7, 9, 12, 0, 0, tzinfo=UTC)
INBOX = "d167d635aaaa4bbbccccddddeeeeffff"


def _evidence(
    *, booking_count: int | None = None, confirmation_age_h: float | None = None
) -> ClinicEvidence:
    """Build a ClinicEvidence with optional booking / confirmation signals."""
    booking = (
        BookingSignal(count=booking_count, last_seen=NOW - timedelta(hours=1))
        if booking_count is not None
        else None
    )
    confirmation = (
        ConfirmationSignal(confirmed_at=NOW - timedelta(hours=confirmation_age_h))
        if confirmation_age_h is not None
        else None
    )
    return ClinicEvidence(inbox_uuid=INBOX, booking=booking, confirmation=confirmation)


class TestDerivationTeeth:
    """T-D1..T-D6 -- the ruled evidence->stage derivation, two-sided."""

    def test_td1_booking_mail_derives_flowing(self) -> None:
        """T-D1: booking mail => Flowing.

        RED side: a derivation that returns anything other than Flowing for a
        clinic with booking_count>0 (e.g. Verified, or None) FAILS here.
        """
        result = derive_stage(_evidence(booking_count=50), NOW)
        assert result is ForwardingStage.FLOWING

    def test_td2_confirmation_silent_past_48h_derives_stalled(self) -> None:
        """T-D2: confirmation + zero booking + older than 48h => Stalled.

        RED side: treating a >48h-silent confirmation as Verified (not aging it
        into Stalled) FAILS -- the silence past the threshold IS the stall.
        """
        result = derive_stage(_evidence(confirmation_age_h=72), NOW)
        assert result is ForwardingStage.STALLED

    def test_td3_recent_confirmation_no_mail_derives_verified(self) -> None:
        """T-D3: confirmation < 48h + no booking => Verified.

        RED side: aging a fresh (6h) confirmation into Stalled FAILS -- the
        clinic is verified and inside the grace window, too early to call stalled.
        """
        result = derive_stage(_evidence(confirmation_age_h=6), NOW)
        assert result is ForwardingStage.VERIFIED

    def test_td4_no_evidence_derives_no_stamp(self) -> None:
        """T-D4: no evidence => NO STAMP (honest absence, G-DENOM).

        RED side: returning ANY stage for a clinic with zero booking mail and no
        confirmation FAILS -- absence must be honest (None), the board stays
        empty rather than asserting an unsupported state.
        """
        result = derive_stage(_evidence(), NOW)
        assert result is None

    def test_td5_never_derives_live(self) -> None:
        """T-D5 (headline teeth): NO evidence ever derives Live.

        Live is the satellite ``first_booking`` receipt; monolith booking volume
        proves forwarding is FLOWING, not satellite-era end-to-end. A huge
        booking count still derives Flowing, never Live.

        RED side: any impl that maps high booking volume to Live FAILS. We also
        exhaustively assert Live is not in the derivation image across a spread of
        evidence shapes.
        """
        assert derive_stage(_evidence(booking_count=999), NOW) is ForwardingStage.FLOWING

        # Exhaustive: Live never appears across the evidence space.
        shapes = [
            _evidence(),
            _evidence(booking_count=0),
            _evidence(booking_count=1),
            _evidence(booking_count=999),
            _evidence(confirmation_age_h=1),
            _evidence(confirmation_age_h=49),
            _evidence(confirmation_age_h=1000),
            _evidence(booking_count=5, confirmation_age_h=1000),
        ]
        for ev in shapes:
            assert derive_stage(ev, NOW) is not ForwardingStage.LIVE

    def test_td6_booking_dominates_stale_confirmation(self) -> None:
        """T-D6: booking mail + an old confirmation => Flowing (mail wins).

        RED side: a clinic with BOTH booking mail AND a >48h-old confirmation
        deriving Stalled FAILS -- the live mail proves it is flowing NOW; the old
        stall signal is moot.
        """
        result = derive_stage(_evidence(booking_count=3, confirmation_age_h=1000), NOW)
        assert result is ForwardingStage.FLOWING

    def test_td5b_zero_booking_count_is_no_evidence(self) -> None:
        """T-D5b (boundary): booking signal present but count==0 is NOT Flowing.

        RED side: treating a booking SIGNAL (present but count 0) as booking mail
        observed FAILS -- only count>0 is 'mail observed'. With no confirmation,
        count==0 alone => NO STAMP.
        """
        assert derive_stage(_evidence(booking_count=0), NOW) is None

    def test_td_boundary_exactly_48h_is_verified_not_stalled(self) -> None:
        """Threshold boundary: a confirmation at EXACTLY 48h is Verified.

        The rule is 'older than the threshold' (strictly >48h) => Stalled. At
        exactly 48h the clinic is still Verified.

        RED side: an off-by-one that treats ==48h as Stalled FAILS.
        """
        result = derive_stage(_evidence(confirmation_age_h=48), NOW)
        assert result is ForwardingStage.VERIFIED

    def test_td_threshold_is_injectable(self) -> None:
        """The nudge threshold is a parameter (deterministic, testable).

        RED side: a hardcoded 48 that ignores the override FAILS -- a 24h
        threshold ages a 30h confirmation into Stalled.
        """
        ev = _evidence(confirmation_age_h=30)
        assert derive_stage(ev, NOW, nudge_threshold_hours=24) is ForwardingStage.STALLED
        assert derive_stage(ev, NOW, nudge_threshold_hours=48) is ForwardingStage.VERIFIED


def test_derivation_image_is_subset_of_the_ruled_domain() -> None:
    """The derivation image is exactly {Flowing, Stalled, Verified, None}.

    RED side: any evidence deriving Sent/Approved/Inactive/Live FAILS. This is
    the structural teeth around ADR-BF-001's ruled domain.
    """
    allowed = {ForwardingStage.FLOWING, ForwardingStage.STALLED, ForwardingStage.VERIFIED, None}
    for bc in (None, 0, 1, 100):
        for age in (None, 1, 47, 48, 49, 1000):
            got = derive_stage(
                ClinicEvidence(
                    inbox_uuid=INBOX,
                    booking=(BookingSignal(bc, NOW) if bc is not None else None),
                    confirmation=(
                        ConfirmationSignal(NOW - timedelta(hours=age)) if age is not None else None
                    ),
                ),
                NOW,
            )
            assert got in allowed, f"derived {got!r} for booking={bc} age={age}"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
