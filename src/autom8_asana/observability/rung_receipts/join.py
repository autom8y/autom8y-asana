"""The join engine for RUNG E limb (a).

LEFT-joins live *delivery* receipts (``report_posted``) to *generation*
provenance (``report_generated``) on ``invocation_id``, then aggregates into a
limb (a) observation.

The join is a LEFT join anchored on delivery: a generation receipt with no
matching delivery is NOT a delivery occurrence (nothing was delivered), and a
delivery with no matching generation is a delivery whose authorship is
un-attested -- which is exactly the current live state (module docstring of
``schema.py``). Neither side may borrow the other's identity: the match is on
``invocation_id`` alone, so a generation receipt from tick X can never clear a
delivery from tick Y.

RUNG-E-limb-(a)-observable for a single occurrence requires ALL of:
  1. a delivery receipt is present (something reached the channel), AND
  2. a generation receipt is present (authorship is attested at all), AND
  3. ``assembled_by == machine`` AND ``human_in_loop is False`` (no human
     assembled it), AND
  4. if both sides carry ``block_count``/``content_hash`` they must agree
     (the delivered artifact is the generated one, not a swap).

Anything short of that yields ``NOT_OBSERVABLE`` with a machine-readable
reason -- the instrument OBSERVES the gap rather than letting a delivery pass
as if a human had never been possible.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8_asana.observability.rung_receipts.schema import (
    LIMB_A_REQUIRED_OCCURRENCES,
    Assembler,
    DeliveryOccurrenceReceipt,
    DeliveryReceipt,
    GenerationReceipt,
    LimbAObservation,
    LimbAStatus,
    NotObservableReason,
    RungEObservability,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


def _classify(
    delivery: DeliveryReceipt | None,
    generation: GenerationReceipt | None,
) -> tuple[RungEObservability, NotObservableReason | None]:
    """Return the RUNG-E limb (a) verdict for one joined occurrence."""
    if delivery is None:
        return RungEObservability.NOT_OBSERVABLE, NotObservableReason.NOT_DELIVERED
    if generation is None:
        # The live state today: delivered, but no authorship provenance exists.
        return (
            RungEObservability.NOT_OBSERVABLE,
            NotObservableReason.GENERATION_PROVENANCE_ABSENT,
        )
    if generation.human_in_loop:
        return RungEObservability.NOT_OBSERVABLE, NotObservableReason.HUMAN_IN_LOOP
    if generation.assembled_by is not Assembler.MACHINE:
        return (
            RungEObservability.NOT_OBSERVABLE,
            NotObservableReason.ASSEMBLED_BY_HUMAN,
        )
    # Bind the delivered artifact to the generated one when both sides carry a
    # block_count -- a mismatch means a different payload was delivered than the
    # one whose machine-authorship was attested.
    if (
        generation.block_count
        and delivery.block_count
        and generation.block_count != delivery.block_count
    ):
        return (
            RungEObservability.NOT_OBSERVABLE,
            NotObservableReason.CONTENT_HASH_MISMATCH,
        )
    return RungEObservability.OBSERVABLE, None


def join_occurrences(
    delivery_events: Iterable[Mapping[str, object]],
    generation_events: Iterable[Mapping[str, object]],
) -> list[DeliveryOccurrenceReceipt]:
    """Join raw delivery + generation log events into occurrence receipts.

    Args:
        delivery_events: raw ``report_posted`` events (dicts).
        generation_events: raw ``report_generated`` events (dicts). Empty in
            the current live state.

    Returns:
        One ``DeliveryOccurrenceReceipt`` per delivered invocation, ordered by
        ``delivered_at`` then ``invocation_id`` for stable output.
    """
    deliveries: dict[str, DeliveryReceipt] = {}
    for evt in delivery_events:
        d_rec = DeliveryReceipt.from_event(dict(evt))
        # Last write wins is fine: report_posted fires once per invocation.
        deliveries[d_rec.invocation_id] = d_rec

    generations: dict[str, GenerationReceipt] = {}
    for evt in generation_events:
        g_rec = GenerationReceipt.from_event(dict(evt))
        generations[g_rec.invocation_id] = g_rec

    receipts: list[DeliveryOccurrenceReceipt] = []
    for inv_id, delivery in deliveries.items():
        generation = generations.get(inv_id)
        status, reason = _classify(delivery, generation)
        receipts.append(
            DeliveryOccurrenceReceipt(
                invocation_id=inv_id,
                delivery=delivery,
                generation=generation,
                rung_e_limb_a_attestation=status,
                rung_e_not_observable_reason=reason,
            )
        )

    receipts.sort(key=lambda r: (r.delivery.delivered_at if r.delivery else "", r.invocation_id))
    return receipts


def observe_limb_a(
    receipts: Iterable[DeliveryOccurrenceReceipt],
) -> LimbAObservation:
    """Aggregate occurrence receipts into a limb (a) observation.

    SATISFIED iff at least ``LIMB_A_REQUIRED_OCCURRENCES`` DISTINCT invocations
    are each RUNG-E-observable.
    """
    receipts = list(receipts)
    observable_ids = [
        r.invocation_id
        for r in receipts
        if r.rung_e_limb_a_attestation is RungEObservability.OBSERVABLE
    ]
    distinct_observable = sorted(set(observable_ids))
    status = (
        LimbAStatus.SATISFIED
        if len(distinct_observable) >= LIMB_A_REQUIRED_OCCURRENCES
        else LimbAStatus.NOT_YET_OBSERVED
    )
    return LimbAObservation(
        status=status,
        observable_occurrences=len(distinct_observable),
        required_occurrences=LIMB_A_REQUIRED_OCCURRENCES,
        observable_invocation_ids=distinct_observable,
        receipts=receipts,
    )
