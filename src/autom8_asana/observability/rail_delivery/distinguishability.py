"""D-1..D-4 — the four distinguishability duties, with a per-duty receipt each.

EX-6 design limb (shape §EX-6, exit criterion 1-2). Duties, not suggestions
(``RAILS-insight-delivery-verified-2026-08-12.md:595-607``).

The doctrine this module makes executable
-----------------------------------------
D-1..D-4 are **jointly sufficient** for glance-level distinguishability at every
surface Slack renders (channel body, notification, mobile preview, search). A
readout satisfying three of four is **not 75% distinguishable — it is
indistinguishable at the surface it missed** (shape §EX-6 exit crit 1). Hence
``DistinguishabilityReceipt.distinguishable`` is the AND of all four, and the
receipt names ``missed_surfaces`` so the failure points at the exact surface.

The four surfaces (RAILS…:604-607):

* **D-1 header** — MUST NOT begin with a reserved header prefix. The header is
  the first and largest visual token.
* **D-2 identity glyph** — MUST carry a distinct glyph that is unused in the
  channel; and no alert glyph may leak anywhere in the blocks. Direct
  application of the "one token, one meaning" rule.
* **D-3 context footer** — MUST name a distinct producer, not the incumbent's
  provenance line.
* **D-4 fallback ``text``** — MUST be distinct and must not open like the
  incumbent. ``text`` is the **notification/mobile line — the only thing many
  readers see**, and its failure mode is SILENT. This duty is receipted **at the
  ``text`` surface**, never the desktop blocks (shape §EX-6 exit crit 2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from autom8_asana.observability.rail_delivery.occupants import (
    DEFAULT_ACCOUNT_HEALTH_OCCUPANTS,
    ChannelOccupants,
)

# A Slack Block Kit block. Values are heterogeneous (str / bool / nested dict /
# list), so ``object`` is the honest element type.
Block = dict[str, object]

# Slack emoji shortcodes: :name: with lowercase letters, digits, _ + -.
_GLYPH_RE = re.compile(r":[a-z0-9][a-z0-9_+\-]*:")


@dataclass(frozen=True)
class DutyReceipt:
    """One duty's verdict at one surface."""

    duty: str  # "D-1".."D-4"
    surface: str  # "header" | "identity_glyph" | "context_footer" | "fallback_text"
    passed: bool
    detail: str
    observed: str | None = None  # the chosen / offending token at this surface
    collided_with: str | None = None  # the reserved token it matched, when failed

    def to_dict(self) -> dict[str, object]:
        return {
            "duty": self.duty,
            "surface": self.surface,
            "passed": self.passed,
            "detail": self.detail,
            "observed": self.observed,
            "collided_with": self.collided_with,
        }


@dataclass(frozen=True)
class DistinguishabilityReceipt:
    """Joint verdict — distinguishable iff ALL FOUR duties pass."""

    distinguishable: bool
    duties: tuple[DutyReceipt, ...]
    missed_surfaces: tuple[str, ...]
    occupants_provenance: str

    def to_dict(self) -> dict[str, object]:
        return {
            "distinguishable": self.distinguishable,
            "missed_surfaces": list(self.missed_surfaces),
            "occupants_provenance": self.occupants_provenance,
            "duties": [d.to_dict() for d in self.duties],
        }


# --- block-surface extraction ---------------------------------------------


def _block_text(block: Block) -> str:
    """Best-effort text of a single Slack Block Kit block."""
    text = block.get("text")
    if isinstance(text, dict):
        return str(text.get("text", ""))
    if isinstance(text, str):
        return text
    elements = block.get("elements")
    if isinstance(elements, list):
        parts = []
        for el in elements:
            if isinstance(el, dict) and isinstance(el.get("text"), str):
                parts.append(el["text"])
        return " ".join(parts)
    return ""


def header_text(blocks: list[Block]) -> str:
    """Text of the first ``header`` block; falls back to the first ``section``."""
    for block in blocks:
        if block.get("type") == "header":
            return _block_text(block)
    for block in blocks:
        if block.get("type") == "section":
            return _block_text(block)
    return ""


def context_footer_text(blocks: list[Block]) -> str:
    """Text of the LAST ``context`` block — the channel's provenance line."""
    for block in reversed(blocks):
        if block.get("type") == "context":
            return _block_text(block)
    return ""


def glyphs_in(text: str) -> list[str]:
    return _GLYPH_RE.findall(text)


def all_glyphs(blocks: list[Block]) -> list[str]:
    found: list[str] = []
    for block in blocks:
        found.extend(glyphs_in(_block_text(block)))
    return found


def _strip_leading_glyphs(text: str) -> str:
    """Normalise a header/text line for prefix comparison.

    Removes glyph shortcodes, then strips leading whitespace/punctuation and
    lowercases so ":bar_chart:  Insights Readout" and "Account Status
    Reconciliation -- ..." compare on their first *word*, not their decoration.
    """
    without_glyphs = _GLYPH_RE.sub("", text)
    lowered = without_glyphs.strip().lower()
    lowered = re.sub(r"^[^a-z0-9]+", "", lowered)
    return re.sub(r"\s+", " ", lowered)


def _identity_glyph_from_blocks(blocks: list[Block]) -> str | None:
    """Derive the identity glyph: the first glyph in the header block."""
    header = ""
    for block in blocks:
        if block.get("type") == "header":
            header = _block_text(block)
            break
    header_glyphs = glyphs_in(header)
    if header_glyphs:
        return header_glyphs[0]
    # fall back to the first glyph anywhere (top-of-message = identity position)
    everywhere = all_glyphs(blocks)
    return everywhere[0] if everywhere else None


# --- the four duties -------------------------------------------------------


def check_d1_header(blocks: list[Block], occupants: ChannelOccupants) -> DutyReceipt:
    header = header_text(blocks)
    normalised = _strip_leading_glyphs(header)
    for prefix in occupants.reserved_header_prefixes:
        if normalised.startswith(prefix):
            return DutyReceipt(
                duty="D-1",
                surface="header",
                passed=False,
                detail=(
                    "header opens with a reserved prefix — both live occupants "
                    "open this way, so this is indistinguishable at the largest "
                    "visual token"
                ),
                observed=header,
                collided_with=prefix,
            )
    if not normalised:
        return DutyReceipt(
            duty="D-1",
            surface="header",
            passed=False,
            detail="no header block present — the readout has no leading identity token",
            observed=header or None,
        )
    return DutyReceipt(
        duty="D-1",
        surface="header",
        passed=True,
        detail="header does not open with any reserved occupant prefix",
        observed=header,
    )


def check_d2_glyph(
    blocks: list[Block],
    occupants: ChannelOccupants,
    identity_glyph: str | None = None,
) -> DutyReceipt:
    glyph = identity_glyph if identity_glyph is not None else _identity_glyph_from_blocks(blocks)

    # (a) an alert glyph leaking ANYWHERE reads as an alert.
    for g in all_glyphs(blocks):
        if g in occupants.reserved_alert_glyphs:
            return DutyReceipt(
                duty="D-2",
                surface="identity_glyph",
                passed=False,
                detail=(
                    "a reserved alert glyph appears in the readout — it carries a "
                    "fixed alert meaning channel-wide and makes the readout read "
                    "as an alert"
                ),
                observed=g,
                collided_with=g,
            )

    # (b) the readout must actually carry a distinct identity glyph.
    if not glyph:
        return DutyReceipt(
            duty="D-2",
            surface="identity_glyph",
            passed=False,
            detail="no distinct identity glyph chosen — the readout has no positive glyph token",
            observed=None,
        )

    # (c) the identity glyph may be neither an alert glyph nor the truncation glyph.
    if glyph in occupants.reserved_identity_glyphs:
        return DutyReceipt(
            duty="D-2",
            surface="identity_glyph",
            passed=False,
            detail=(
                "identity glyph is reserved in this channel (alert or truncation "
                "meaning) — reusing it collapses one-token-one-meaning"
            ),
            observed=glyph,
            collided_with=glyph,
        )

    note = (
        ""
        if occupants.sdk_severity_glyphs_complete
        else (
            " [reserved-alert set is the verbatim-known seed, not the full SDK "
            "severity set — see occupants UV-P]"
        )
    )
    return DutyReceipt(
        duty="D-2",
        surface="identity_glyph",
        passed=True,
        detail=f"identity glyph is distinct and unused in this channel{note}",
        observed=glyph,
    )


def check_d3_footer(blocks: list[Block], occupants: ChannelOccupants) -> DutyReceipt:
    footer = context_footer_text(blocks)
    normalised = footer.strip().lower()
    for producer in occupants.reserved_footer_producers:
        if producer.lower() in normalised:
            return DutyReceipt(
                duty="D-3",
                surface="context_footer",
                passed=False,
                detail=(
                    "context footer reuses the incumbent's provenance line — it "
                    "attributes the readout to the aborting service"
                ),
                observed=footer,
                collided_with=producer,
            )
    if not normalised:
        return DutyReceipt(
            duty="D-3",
            surface="context_footer",
            passed=False,
            detail="no context footer present — the readout names no distinct producer",
            observed=footer or None,
        )
    return DutyReceipt(
        duty="D-3",
        surface="context_footer",
        passed=True,
        detail="context footer names a distinct producer",
        observed=footer,
    )


def check_d4_fallback_text(text: str, occupants: ChannelOccupants) -> DutyReceipt:
    """D-4 — inspected at the FALLBACK ``text`` surface (notification / mobile).

    This deliberately takes ``text`` and NOT the blocks: ``text`` is the only
    surface a mobile push / notification renders, its failure is silent, and a
    receipt that inspects only the desktop blocks does NOT discharge D-4
    (shape §EX-6 exit crit 2).
    """
    surface = "fallback_text"
    if not text or not text.strip():
        return DutyReceipt(
            duty="D-4",
            surface=surface,
            passed=False,
            detail=(
                "fallback text is empty — the notification/mobile line, the only "
                "thing many readers see, carries no distinguishing content"
            ),
            observed=text or None,
        )
    normalised = _strip_leading_glyphs(text)
    for prefix in occupants.reserved_text_prefixes:
        if normalised.startswith(prefix):
            return DutyReceipt(
                duty="D-4",
                surface=surface,
                passed=False,
                detail=(
                    "fallback text (the notification/mobile line) opens like the "
                    "incumbent — silent collision on the surface many readers only "
                    "ever see"
                ),
                observed=text,
                collided_with=prefix,
            )
    return DutyReceipt(
        duty="D-4",
        surface=surface,
        passed=True,
        detail=(
            "fallback text (notification/mobile surface, inspected directly — not "
            "the desktop blocks) is distinct and does not open like the incumbent"
        ),
        observed=text,
    )


def evaluate(
    blocks: list[Block],
    text: str,
    *,
    identity_glyph: str | None = None,
    occupants: ChannelOccupants = DEFAULT_ACCOUNT_HEALTH_OCCUPANTS,
) -> DistinguishabilityReceipt:
    """Run all four duties jointly and return the joint receipt.

    ``distinguishable`` is the AND of the four — three-of-four is a fail, and
    ``missed_surfaces`` names where.
    """
    duties = (
        check_d1_header(blocks, occupants),
        check_d2_glyph(blocks, occupants, identity_glyph),
        check_d3_footer(blocks, occupants),
        check_d4_fallback_text(text, occupants),
    )
    missed = tuple(d.surface for d in duties if not d.passed)
    return DistinguishabilityReceipt(
        distinguishable=all(d.passed for d in duties),
        duties=duties,
        missed_surfaces=missed,
        occupants_provenance=occupants.provenance,
    )
