"""Pure evidence->stage derivation for the Forwarding-Stage backfill (S4).

The board tells a partial truth: only the handful of clinics the operator
hand-stamped carry any Forwarding Stage, while the whole flowing book (~60
clinic inboxes moving hundreds of booking mails/week through the legacy
monolith) has no machine-derived stage. Pre-flip, EBI is dark -- there are NO
satellite witness rows -- so the ONLY truth about which clinics are flowing,
stalled, or verified is the monolith's own ``/ecs/monolith-prod`` logs.

This module is the ONE new pure function S4 adds: ``derive_stage`` maps a
clinic's log-derived evidence to a *proposed* :class:`ForwardingStage` (or
``None`` -- honest absence). That proposed stage is then fed through the
UNCHANGED S1 :class:`StageTransitionValidator` by the application layer, so the
never-downgrade / fail-closed / idempotence guarantees come FREE from S1.

Purity contract (Clean-Architecture / DIP): this module depends on NOTHING in
the infrastructure layer -- no CloudWatch client, no boto3, no I/O. It imports
only the pure ``ForwardingStage`` enum and takes plain dataclasses + a clock.
Every rule below is a pure function, exhaustively unit-testable with no mocks
(the two-sided teeth target, TDD S4 T-D1..T-D6).

Derivation domain (ADR-BF-001): ``{Flowing, Stalled, Verified}`` union
``{NO STAMP}`` -- **NEVER** ``Live`` (Live is the satellite ``first_booking``
receipt; monolith booking volume proves *forwarding is flowing*, NOT that the
*satellite* completed an end-to-end booking -- stamping Live from monolith
volume would falsely claim satellite-era end-to-end). Never ``Sent`` /
``Approved`` (human affordances) / ``Inactive`` (human de-enrollment).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from autom8_asana.domain.forwarding_stage import ForwardingStage

if TYPE_CHECKING:
    from datetime import datetime

#: The default nudge/stall threshold (hours). Mirrors the S1 nudge->Stalled
#: semantics ("verified but silent past N hours"). A verified-but-silent clinic
#: crosses into Stalled once its confirmation is older than this.
DEFAULT_NUDGE_THRESHOLD_HOURS = 48


@dataclass(frozen=True)
class BookingSignal:
    """Per-clinic booking-mail evidence over the lookback window.

    ``count`` is the number of real (non-forwarding) inbound booking mails that
    reached the booking pipeline for this inbox in the window; ``last_seen`` is
    the timestamp of the most recent one. A clinic with ``count > 0`` is
    demonstrably forwarding-live in the window.
    """

    count: int
    last_seen: datetime


@dataclass(frozen=True)
class ConfirmationSignal:
    """Per-clinic forwarding-confirmation evidence over the lookback window.

    ``confirmed_at`` is the timestamp of the most recent forwarding-confirmation
    event (the ``classify_forwarding_email`` HIT). Its presence proves the
    clinic was verified; the age of it (vs the nudge threshold) discriminates
    Verified (recent) from Stalled (silent-past-threshold).
    """

    confirmed_at: datetime


@dataclass(frozen=True)
class ClinicEvidence:
    """All log-derived evidence for one clinic, keyed by its inbox uuid.

    ``inbox_uuid`` is the mailbox local-part (== ``chiropractor_guid`` ==
    the Asana "Company ID" custom-field value the CI-task resolution searches
    on -- the tenant key crossing every boundary). ``booking`` / ``confirmation``
    are ``None`` when the respective signal is absent in the window.
    """

    inbox_uuid: str
    booking: BookingSignal | None
    confirmation: ConfirmationSignal | None


def derive_stage(
    evidence: ClinicEvidence,
    now: datetime,
    *,
    nudge_threshold_hours: int = DEFAULT_NUDGE_THRESHOLD_HOURS,
) -> ForwardingStage | None:
    """Derive the *proposed* Forwarding Stage from a clinic's log evidence.

    Pure function; no I/O. The RULED derivation (ADR-BF-001), each row mapping a
    machine-stage semantic from S1 verbatim:

    - ``>=1`` booking mail in the window       -> ``Flowing``   (S1 mail_observed)
    - forwarding-confirmation, no booking mail, confirmation older than the
      nudge threshold                          -> ``Stalled``   (S1 nudge)
    - forwarding-confirmation recent (< threshold), no booking mail
                                               -> ``Verified``  (S1 verified)
    - no evidence at all                       -> ``None``      (NO STAMP; honest
                                                                 absence, G-DENOM)

    Booking mail DOMINATES a stale confirmation: a clinic that is both booking
    AND has an old confirmation is ``Flowing`` (the mail proves it is flowing
    NOW; the stall signal is moot -- T-D6). ``Live`` is NEVER derived (T-D5):
    the domain of this function is ``{Flowing, Stalled, Verified}`` union
    ``{None}``.

    Args:
        evidence: the clinic's log-derived signals.
        now: the reference "now" used to age the confirmation (injected so the
            derivation is deterministic and testable without a real clock).
        nudge_threshold_hours: hours after which a silent confirmation is
            Stalled rather than Verified (default 48, mirrors S1).

    Returns:
        The proposed ``ForwardingStage`` (one of Flowing / Stalled / Verified),
        or ``None`` when the evidence does not support any stamp.
    """
    has_booking = evidence.booking is not None and evidence.booking.count > 0

    # 1. Booking mail observed -> Flowing. This dominates a stale confirmation:
    #    the mail proves the clinic is forwarding-live NOW regardless of an old
    #    verification event (T-D1, T-D6).
    if has_booking:
        return ForwardingStage.FLOWING

    # 2. No booking mail. If a forwarding-confirmation exists, discriminate
    #    Verified (recent, inside the grace window) from Stalled (silent past
    #    the nudge threshold).
    if evidence.confirmation is not None:
        age_hours = (now - evidence.confirmation.confirmed_at).total_seconds() / 3600.0
        if age_hours > nudge_threshold_hours:
            # Verified-but-silent past the threshold -> the silence IS the stall
            # (T-D2). Off-spine overlay; the S1 validator gates it downstream.
            return ForwardingStage.STALLED
        # Verified, still inside the grace window; too early to call it stalled
        # (T-D3).
        return ForwardingStage.VERIFIED

    # 3. No booking mail, no confirmation -> NO STAMP. Absence is honest: the
    #    board stays empty/human-set for this clinic rather than asserting a
    #    state the logs do not support (T-D4, G-DENOM).
    return None


__all__ = [
    "DEFAULT_NUDGE_THRESHOLD_HOURS",
    "BookingSignal",
    "ClinicEvidence",
    "ConfirmationSignal",
    "derive_stage",
]
