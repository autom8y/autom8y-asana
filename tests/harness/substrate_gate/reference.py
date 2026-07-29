"""Reference + deliberately-broken substrates for harness self-test (S7 · P5).

OVER-CLAIM GUARD (architect S7 ruling, obeyed): ``ReferenceSubstrate`` is a MINIMAL
harness-internal serve oracle that exists ONLY to prove the replay runner's teeth on
known fixtures. It is **NOT v2's serve** (which does not exist until S5/S8) and makes
**no v2-parity claim**. It does not call the SEAM-0 ``substrate.freshness.is_provable``
(that raises ``NotImplementedError`` — owned by S2); it re-derives a minimal age /
digest / divergence gate itself, purely so the harness has a known-correct
counter-party to discriminate against the broken substrates below.

``SilentServeSubstrate`` and ``OverRefuseSubstrate`` are the negative-space fixtures:
a runner that always answered PASS could not tell them from the reference. They make
the two-sided teeth falsifiable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8_asana.substrate.freshness import FreshnessProof
from autom8_asana.substrate.serve import Provable, Refused, RefusePayload, RefuseReason
from tests.harness.substrate_gate.cases import HarnessRefusePayload, SunsetBreach
from tests.harness.substrate_gate.divergence import divergence_payload, diverges, order_by_age
from tests.harness.substrate_gate.frame_codec import FrameContent, encode_frame

if TYPE_CHECKING:
    from datetime import datetime

    from autom8_asana.substrate.serve import ServedNumber
    from tests.harness.substrate_gate.cases import Materialization, SeededState


def _empty_payload() -> RefusePayload:
    """A well-formed payload for a no-copy (MISSING) refusal — multiplicity kept, empty."""
    return RefusePayload(plane="", absolute_age={}, magnitude=0.0, per_section_delta={})


def _single_copy_payload(materialization: Materialization, age: float) -> RefusePayload:
    """A well-formed payload for a single-copy refusal (STALE/CORRUPT): one age entry."""
    return RefusePayload(
        plane=materialization.plane,
        absolute_age={materialization.plane: age},
        magnitude=0.0,
        per_section_delta={},
    )


def _sunset_payload(
    materialization: Materialization, age: float, *, sunset_after: datetime, observed_at: datetime
) -> HarnessRefusePayload:
    """The C13-marked payload for a sunset-breach refusal: STALE + named marker.

    The four frozen fields land exactly as in ``_single_copy_payload``; the 5th
    additive ``sunset_breach`` field makes the breach machine-distinguishable.
    """
    return HarnessRefusePayload(
        plane=materialization.plane,
        absolute_age={materialization.plane: age},
        magnitude=0.0,
        per_section_delta={},
        sunset_breach=SunsetBreach(
            surface=materialization.plane, sunset_after=sunset_after, observed_at=observed_at
        ),
    )


class ReferenceSubstrate:
    """Minimal CORRECT serve oracle for self-test — NOT v2's serve (see module docstring).

    Gate order: MISSING → DIVERGENT → CORRUPT → STALE → (RC-D sunset) → Provable.
    """

    def serve(self, state: SeededState) -> ServedNumber:
        materializations = state.materializations
        if not materializations:
            return Refused(reason=RefuseReason.MISSING, detail=_empty_payload())

        canonical = materializations[0]
        for other in materializations[1:]:
            if diverges(canonical, other):
                stale, fresh = order_by_age(canonical, other)
                return Refused(
                    reason=RefuseReason.DIVERGENT,
                    detail=divergence_payload(stale, fresh, now=state.now),
                )

        age = (state.now - canonical.proof.built_from_live_at).total_seconds()
        if canonical.frame_digest != canonical.proof.content_digest:
            return Refused(reason=RefuseReason.CORRUPT, detail=_single_copy_payload(canonical, age))
        if age > canonical.proof.sla_seconds:
            return Refused(reason=RefuseReason.STALE, detail=_single_copy_payload(canonical, age))
        if state.sunset_after is not None and state.now > state.sunset_after:
            # RC-D: a bridge past its machine-enforced sunset fails loud.
            # sunset→STALE per the frozen CLOSED RefuseReason grammar (TDD §11 C13,
            # architect ruling 2026-07-29): the enum stays closed — the breach is
            # machine-distinguishable via the additive sunset_breach payload marker,
            # never via a new enum member (the EXPIRED rot-trigger is recorded in C13).
            return Refused(
                reason=RefuseReason.STALE,
                detail=_sunset_payload(
                    canonical, age, sunset_after=state.sunset_after, observed_at=state.now
                ),
            )

        content = FrameContent(
            served_value=canonical.served_value,
            plane=canonical.plane,
            composition=canonical.composition,
        )
        return Provable(frame=encode_frame(content), proof=canonical.proof)


class SilentServeSubstrate:
    """DELIBERATELY BROKEN: serves the first copy regardless of staleness/divergence.

    The exact v1 wound — a number the system cannot prove, served under a green
    proof. The harness must FAIL this on every BROKEN case.
    """

    def serve(self, state: SeededState) -> ServedNumber:
        if not state.materializations:
            content = FrameContent(served_value=0.0, plane="silent-empty", composition={})
            zero_proof = FreshnessProof(
                built_from_live_at=state.now, content_digest="", sla_seconds=0
            )
            return Provable(frame=encode_frame(content), proof=zero_proof)
        materialization = state.materializations[0]
        content = FrameContent(
            served_value=materialization.served_value,
            plane=materialization.plane,
            composition=materialization.composition,
        )
        return Provable(frame=encode_frame(content), proof=materialization.proof)


class OverRefuseSubstrate:
    """DELIBERATELY BROKEN: refuses even healthy inputs (alarm noise).

    The two-sided complement of ``SilentServeSubstrate``. The harness must FAIL this
    on every GOOD case.
    """

    def serve(self, state: SeededState) -> ServedNumber:
        if state.materializations:
            materialization = state.materializations[0]
            age = (state.now - materialization.proof.built_from_live_at).total_seconds()
            return Refused(
                reason=RefuseReason.STALE, detail=_single_copy_payload(materialization, age)
            )
        return Refused(reason=RefuseReason.MISSING, detail=_empty_payload())
