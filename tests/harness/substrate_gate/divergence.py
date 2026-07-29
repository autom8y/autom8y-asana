"""Divergence → ``RefusePayload`` construction (S7 · P5 · RC-A-2 observable).

The single place the harness turns two disagreeing materializations into the
FROZEN RC-A-2 explanation observable, ``substrate.serve.RefusePayload`` — the OQ-1
observable the architect FROZE and instructed **do NOT narrow**:

    plane            — which copy/plane the refusal concerns
    absolute_age     — Mapping[plane -> age-seconds] of EACH copy (multiplicity kept)
    magnitude        — divergence magnitude (fresher served_value − staler served_value)
    per_section_delta — Mapping[section -> value delta] (composition shift, per section)

Both the reference substrate's DIVERGENT branch and the parity runner's per-
divergence ledger construct the payload here, so the four fields land identically
on both surfaces.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8_asana.substrate.serve import RefusePayload

if TYPE_CHECKING:
    from datetime import datetime

    from tests.harness.substrate_gate.cases import Materialization


def _age_seconds(materialization: Materialization, now: datetime) -> float:
    """Absolute age of a copy at ``now`` (seconds since its content-fetch instant)."""
    return (now - materialization.proof.built_from_live_at).total_seconds()


def order_by_age(
    left: Materialization, right: Materialization
) -> tuple[Materialization, Materialization]:
    """Return ``(staler, fresher)`` ordered by ``built_from_live_at`` (older first)."""
    if left.proof.built_from_live_at <= right.proof.built_from_live_at:
        return left, right
    return right, left


def diverges(left: Materialization, right: Materialization, *, abs_tol: float = 0.005) -> bool:
    """True iff the two copies disagree on the served value beyond ``abs_tol``."""
    return abs(left.served_value - right.served_value) > abs_tol


def divergence_payload(
    stale: Materialization, fresh: Materialization, *, now: datetime
) -> RefusePayload:
    """Build the FROZEN RC-A-2 ``RefusePayload`` from a (stale, fresh) copy pair.

    ``plane`` names the STALE copy — the one at risk of a silent wrong-serve.
    ``magnitude`` and ``per_section_delta`` are ``fresh − stale`` (so a coherent
    composition shift sums: Σ per_section_delta == magnitude).
    """
    sections = sorted(set(stale.composition) | set(fresh.composition))
    per_section_delta: dict[str, float] = {}
    for name in sections:
        stale_value = stale.composition[name].value if name in stale.composition else 0.0
        fresh_value = fresh.composition[name].value if name in fresh.composition else 0.0
        per_section_delta[name] = fresh_value - stale_value
    return RefusePayload(
        plane=stale.plane,
        absolute_age={
            stale.plane: _age_seconds(stale, now),
            fresh.plane: _age_seconds(fresh, now),
        },
        magnitude=fresh.served_value - stale.served_value,
        per_section_delta=per_section_delta,
    )


def explain_divergence(payload: RefusePayload, *, baseline_value: float | None = None) -> str:
    """Render a one-line 'composition shift, not noise' explanation from the payload.

    Names each CHANGED section's signed delta and the net magnitude (with % when a
    baseline is given). This is the human-readable projection of the four frozen
    fields — the ``per_section_delta`` mapping itself stays COMPLETE and un-narrowed
    (zero-delta sections are omitted from the prose only, never from the observable).
    """
    parts = [
        f"{name} {_signed_dollars(delta)}"
        for name, delta in sorted(payload.per_section_delta.items())
        if delta != 0.0
    ]
    movement = ", ".join(parts) if parts else "no per-section movement"
    net = _signed_dollars(payload.magnitude)
    pct = ""
    if baseline_value:
        pct = f" / {payload.magnitude / baseline_value * 100:+.0f}%"
    return f"composition shift, not noise: {movement} (net {net}{pct})"


def _signed_dollars(value: float) -> str:
    """Format a signed dollar delta, e.g. ``-$4,000`` / ``+$4,800``."""
    sign = "-" if value < 0 else "+"
    return f"{sign}${abs(value):,.0f}"
