"""Block budget + overflow — declared explicitly, never truncated silently.

EX-6 design limb (shape §EX-6 exit crit 4-5). Inherited constraint at
``RAILS-insight-delivery-verified-2026-08-12.md:643-708`` (§6).

The two facts this module refuses to let a readout forget
---------------------------------------------------------
1. **Slack truncates at 50 blocks with NO marker of any kind** (RAILS…:653,
   ``report.py:77-82`` verbatim). An overflow does not *look* like an error — it
   looks like a shorter report. A recurring readout that silently drops its tail
   is the "confidently wrong" failure (shape §EX-6 exit crit 4). So a readout
   must either stay provably under budget OR mark its own truncation.
2. **The budget is per MESSAGE, not per channel** (RAILS…:655-660). Sharing
   ``#account-health`` with the aborts costs the readout ZERO blocks — the
   incumbent's 3-block abort bypasses the SDK builder entirely. Co-tenancy (the
   D-1..D-4 problem) and the ceiling (this module) are INDEPENDENT; conflating
   them over-constrains the design. ``plan()`` therefore takes only the readout's
   OWN item count and framing — nothing about channel traffic enters.

Explicit budget (RAILS…:682-688, exit crit 4)
---------------------------------------------
"This artifact deliberately does not name a maximum item count: it depends on
blocks-per-item, which is the generator's design choice. The requirement is that
[the readout] declare its budget explicitly — framing blocks, blocks-per-item,
and the resulting item ceiling — as a stated number, not an emergent one."
``BlockBudget`` is that stated declaration.

Overflow degrades to complete-by-construction summary + marker (RAILS…:689-693)
-------------------------------------------------------------------------------
Following the incumbent's own precedent: *counts complete, sections possibly not,
with an explicit ``:scissors:`` marker*. Completeness is carried by the COUNTS in
the marker ("showing k of n"), NOT by a drill-out pointer — the incumbent's
pointer currently 404s (NF-1, owned by S5, RAILS…:694-708), so a readout may not
rely on drill-out for completeness. ``drill_pointer`` is optional and defaults to
absent for exactly that reason.
"""

from __future__ import annotations

from dataclasses import dataclass

# SDK defaults, per RAILS…:651 (autom8y_reconciliation 2.3.0 report.py:21-22).
DEFAULT_MAX_BLOCKS = 50
DEFAULT_RESERVED_BLOCKS = 10

# One block held back for a possible truncation marker, so the item ceiling is
# safe to fill completely even when the readout overflows and must self-mark.
_MARKER_RESERVE = 1

# The channel's truncation token — one meaning, channel-wide (RAILS…:593-596).
TRUNCATION_GLYPH = ":scissors:"

# A Slack Block Kit block; heterogeneous values -> ``object`` element type.
Block = dict[str, object]


@dataclass(frozen=True)
class BlockBudget:
    """An EXPLICIT, stated budget for one readout message.

    ``framing_blocks`` is the readout's own fixed overhead (header + summary +
    divider + footer) — it does NOT include the optional truncation marker; the
    marker is held back separately (``_MARKER_RESERVE``). ``item_ceiling`` is a
    stated number derived from stated inputs, never emergent.
    """

    framing_blocks: int
    blocks_per_item: int
    max_blocks: int = DEFAULT_MAX_BLOCKS
    reserved_blocks: int = DEFAULT_RESERVED_BLOCKS

    def __post_init__(self) -> None:
        if self.blocks_per_item < 1:
            raise ValueError("blocks_per_item must be >= 1")
        if self.framing_blocks < 0:
            raise ValueError("framing_blocks must be >= 0")
        if self.available_body_blocks < 0:
            raise ValueError(
                "framing_blocks exceeds the usable body budget "
                f"(max={self.max_blocks} - reserved={self.reserved_blocks} "
                f"- framing={self.framing_blocks} < 0)"
            )

    @property
    def available_body_blocks(self) -> int:
        """Blocks available for the body: 50 - reserved - framing (RAILS…:682)."""
        return self.max_blocks - self.reserved_blocks - self.framing_blocks

    @property
    def item_ceiling(self) -> int:
        """Max items that fit, holding one block back for a truncation marker."""
        return max(0, (self.available_body_blocks - _MARKER_RESERVE) // self.blocks_per_item)


@dataclass(frozen=True)
class BudgetReceipt:
    """What ``plan()`` decided, and the proof it stayed under the ceiling."""

    max_blocks: int
    reserved_blocks: int
    framing_blocks: int
    blocks_per_item: int
    item_ceiling: int
    total_items: int
    shown_items: int
    dropped_items: int
    truncated: bool
    truncation_marker_present: bool
    rendered_block_total: int
    within_ceiling: bool  # rendered_block_total <= max_blocks (hard Slack limit)
    complete: bool  # no items dropped — distinct from within_ceiling

    def to_dict(self) -> dict[str, object]:
        return {
            "max_blocks": self.max_blocks,
            "reserved_blocks": self.reserved_blocks,
            "framing_blocks": self.framing_blocks,
            "blocks_per_item": self.blocks_per_item,
            "item_ceiling": self.item_ceiling,
            "total_items": self.total_items,
            "shown_items": self.shown_items,
            "dropped_items": self.dropped_items,
            "truncated": self.truncated,
            "truncation_marker_present": self.truncation_marker_present,
            "rendered_block_total": self.rendered_block_total,
            "within_ceiling": self.within_ceiling,
            "complete": self.complete,
        }


def plan(budget: BlockBudget, total_items: int) -> BudgetReceipt:
    """Decide how many items to show and whether a truncation marker is needed.

    Never silent: if items would overflow, ``shown_items`` is capped at the
    stated ceiling and ``truncation_marker_present`` is True. The invariant
    ``rendered_block_total <= max_blocks`` holds by construction for any
    ``total_items >= 0``.
    """
    if total_items < 0:
        raise ValueError("total_items must be >= 0")

    truncated = total_items > budget.item_ceiling
    shown = min(total_items, budget.item_ceiling)
    dropped = total_items - shown
    marker = truncated  # a self-mark is emitted exactly when we drop items
    rendered_total = budget.framing_blocks + shown * budget.blocks_per_item + (1 if marker else 0)

    return BudgetReceipt(
        max_blocks=budget.max_blocks,
        reserved_blocks=budget.reserved_blocks,
        framing_blocks=budget.framing_blocks,
        blocks_per_item=budget.blocks_per_item,
        item_ceiling=budget.item_ceiling,
        total_items=total_items,
        shown_items=shown,
        dropped_items=dropped,
        truncated=truncated,
        truncation_marker_present=marker,
        rendered_block_total=rendered_total,
        within_ceiling=rendered_total <= budget.max_blocks,
        complete=dropped == 0,
    )


def truncation_marker_block(
    shown: int,
    total: int,
    *,
    glyph: str = TRUNCATION_GLYPH,
    drill_pointer: str | None = None,
) -> Block:
    """A complete-by-construction truncation marker (RAILS…:689-693).

    Completeness is carried by the counts, not the pointer. ``drill_pointer``
    defaults to absent because the incumbent's drill-out currently 404s
    (NF-1, S5). The ``glyph`` is ``:scissors:`` — the channel's truncation token,
    used here on a NON-header block, which is its rule-consistent placement.
    """
    dropped = total - shown
    text = (
        f"{glyph} Showing {shown} of {total}. The counts above are complete; "
        f"{dropped} item(s) are not shown here."
    )
    if drill_pointer:
        text += f" Full detail: {drill_pointer}"
    return {"type": "context", "elements": [{"type": "mrkdwn", "text": text}]}
