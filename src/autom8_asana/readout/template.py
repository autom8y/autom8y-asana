"""The recurring exec readout template — a fixed skeleton with named slots.

EX-5 (WS-2). Implements SPEC-recurring-readout-template-2026-08-13.md §2 as a
pure function ``render_blocks(figure, g4_bound, cadence_label, seq, generated_at)``
returning the assembled block payload (the artifact delivered to Slack). Every
rendered value is derived from the passed figure — no slot is typed by a human.

The template holds four structural fences:
  * §4 / C-6 DENOM-FENCE — the denominator is a TYPED ``k``/``n`` + "sections"
    slot that cannot express an age or a rate.
  * §3 / C-5 — the G4' bound rides ON the number, regenerated per render; a
    block set carrying the number without its bound is malformed.
  * §5 / C-4 / DF-4 — the extension point is a declared, EMPTY, attested-empty
    band; no second (or movement-class) number can enter it here.
  * §6 / R-16 / F-E3 — the orientation footer states what the figure IS and IS
    NOT; it never recommends, ranks, or leads with a call to action.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.readout.item_1a import G4PrimeBound, Item1aFigure


class ReadoutSlot(StrEnum):
    """The named slots of the fixed skeleton (SPEC §2.1)."""

    HEADER = "header"
    SAY_ABLE_NUMBER = "say_able_number"
    G4_PRIME_BOUND = "g4_prime_bound"
    DISCLOSURE = "disclosure"
    EXTENSION_POINT = "extension_point"
    ORIENTATION_FOOTER = "orientation_footer"


class Ex2Disposition(StrEnum):
    """EX-2's disposition, recorded against the extension point (SPEC §5).

    ``STILL_ONE`` is the default and a *legitimate passing outcome* (DF-5): the
    say-able set stays one, the extension point stays empty-and-attested.
    ``ONE_B_PROMOTED`` is reachable only through EX-2's re-derivation (C-4) and
    is NOT selectable by this template alone.
    """

    STILL_ONE = "still_one"
    ONE_B_PROMOTED = "1b_promoted"


@dataclass(frozen=True)
class DenominatorSlot:
    """The C-6 / DENOM-FENCE typed denominator: ``k`` of ``n`` in-scope sections.

    ``k`` and ``n`` are integers and ``unit`` is a section count. The slot is
    typed precisely so a future "different kind of claim" (a rate, a ratio, an
    age, a movement count) CANNOT be admitted by analogy to D-6 — it has no
    field that can carry one. A fourth number must route through the extension
    point + a new operator ruling, not through this slot.
    """

    k: int
    n: int
    unit: str = "sections"

    def render(self) -> str:
        """The in-sentence scope qualifier: ``{k} of {n} in-scope sections``."""
        return f"{self.k} of {self.n} in-scope {self.unit}"


# Orientation footer text — descriptive only (R-16 / F-E3). It states what the
# figure IS and IS NOT and where the alarm lives; it issues NO instruction.
_ORIENTATION_FOOTER = (
    "This is a recency statement — the most recent observed offer edit — not a "
    "completeness guarantee and not a movement count. Freshness alerting is the "
    "warmer-side PROV-family alarm's job, not this readout's: this readout "
    "reports state, the alarm pages."
)


def render_fallback_text(
    figure: Item1aFigure,
    *,
    cadence_label: str,
    seq: int,
    generated_at: str,
) -> str:
    """The D-4 fallback ``text`` surface of the Slack payload.

    A Slack message is ``blocks`` PLUS a top-level ``text`` (the notification /
    accessibility fallback). The ``{blocks, text}`` content-hash contract
    (REC-001, ``observability.payload_hash``) needs a ``text`` to bind, so the
    generation mechanism produces one HERE — deterministically, from the figure,
    with NO human-typed slot (the load-bearing "no human assembled it" invariant
    extends to the fallback text, not just the blocks).

    It restates the ONE say-able number and its typed denominator as a flat
    string. It carries the same recency-not-completeness register as the
    orientation footer; it never recommends, ranks, or steers.
    """
    denom = DenominatorSlot(k=figure.k, n=figure.n)
    return (
        f"{cadence_label} offers readout · occurrence #{seq} · generated "
        f"{generated_at}: the most recent observed offer edit across "
        f"{denom.render()} was {figure.as_of_iso}. Recency statement — not a "
        f"completeness guarantee and not a movement count."
    )


def render_blocks(
    figure: Item1aFigure,
    g4_bound: G4PrimeBound,
    cadence_label: str,
    seq: int,
    generated_at: str,
    ex2_disposition: Ex2Disposition = Ex2Disposition.STILL_ONE,
) -> list[dict[str, object]]:
    """Assemble the readout block payload from item 1a's figure and bound.

    Args:
        figure: the computed item-1a figure (the number + typed denominator).
        g4_bound: the per-render G4' sign statement that must accompany it.
        cadence_label: the ruled cadence's human label (e.g. "Weekly"). Filled
            from the operator's Q-2; a live render is EXIT-HELD until Q-2, but
            the mechanism accepts the label as an argument so it is data-driven.
        seq: the occurrence ordinal — the join key the generation receipt binds.
        generated_at: the generation/observation instant, ISO-8601 UTC — the
            ``{t}`` slot (provenance, NOT a say-able number).
        ex2_disposition: EX-2's recorded disposition for the extension point.

    Returns:
        The ordered block payload: one dict per slot. This IS the artifact whose
        bytes the generation receipt's ``content_hash`` covers.
    """
    denom = DenominatorSlot(k=figure.k, n=figure.n)
    say_able_value = figure.as_of_iso

    return [
        {
            "role": ReadoutSlot.HEADER.value,
            "text": f"{cadence_label} · generated {generated_at} · occurrence #{seq}",
            "cadence_label": cadence_label,
            "seq": seq,
            "generated_at": generated_at,
        },
        {
            "role": ReadoutSlot.SAY_ABLE_NUMBER.value,
            "text": (
                f"As of {generated_at}, the most recent observed offer edit "
                f"across {denom.render()} was {say_able_value}."
            ),
            # The ONE say-able number, structured so a consumer counts exactly
            # one (SC-1). The observation instant and the denominator are NOT
            # say-able numbers and are carried in dedicated, distinct fields.
            "say_able_value": say_able_value,
            "observation_instant": generated_at,
            "denominator": {"k": denom.k, "n": denom.n, "unit": denom.unit},
        },
        {
            "role": ReadoutSlot.G4_PRIME_BOUND.value,
            "text": g4_bound.text,
            "single_signed": g4_bound.single_signed,
            "dominant_sign": g4_bound.dominant_sign.value,
        },
        {
            "role": ReadoutSlot.DISCLOSURE.value,
            "text": (
                "Reads via POST /v1/query/offer/rows; the as-of is the oldest of "
                f"the {figure.k} constituents. This is a recency statement, not "
                "a completeness guarantee and not a movement count."
            ),
        },
        {
            "role": ReadoutSlot.EXTENSION_POINT.value,
            "text": "── extension point (declared, EMPTY) ──",
            # Attested-empty, not merely blank (SC-6): EX-2's disposition is
            # recorded; the second number class stays None until 1b promotes
            # through EX-2's re-derivation (C-4) — never through this template.
            "ex2_disposition": ex2_disposition.value,
            "second_number_class": None,
        },
        {
            "role": ReadoutSlot.ORIENTATION_FOOTER.value,
            "text": _ORIENTATION_FOOTER,
        },
    ]
