"""The readout SHAPE — composes distinguishability + budget into one artifact.

EX-6 design limb. This is the buildable *shape* a readout must take to be both
distinguishable (D-1..D-4) and budgeted (never silently truncated), rendered to
the Slack Block Kit array + fallback ``text`` that the delivery path posts.

The design limb runs PARALLEL with EX-5: EX-5 (the generation mechanism) fills a
``Readout`` with real content; this module fixes its *shape* and proves the shape
is distinguishable and budget-safe against SYNTHETIC content. Nothing here posts
to Slack.

Framing accounting (must match ``BlockBudget.framing_blocks``)
--------------------------------------------------------------
A rendered readout's fixed framing is: header (1) + summary section (1) +
divider (1) + context footer (1) = 4 blocks. Body items follow, then an optional
truncation marker. ``default_budget()`` states this so ``framing_blocks`` is a
declared number, not read off the render.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from autom8_asana.observability.rail_delivery import block_budget as bb
from autom8_asana.observability.rail_delivery import distinguishability as dist
from autom8_asana.observability.rail_delivery.delivery_receipt import DeliveryReceipt
from autom8_asana.observability.rail_delivery.occupants import (
    DEFAULT_ACCOUNT_HEALTH_OCCUPANTS,
    ChannelOccupants,
)

# Fixed framing blocks of a rendered readout: header + summary + divider + footer.
FRAMING_BLOCKS = 4

# A Slack Block Kit block; heterogeneous values -> ``object`` element type.
Block = dict[str, object]


def default_budget(blocks_per_item: int) -> bb.BlockBudget:
    """A budget declared with this module's framing accounting stated explicitly."""
    return bb.BlockBudget(framing_blocks=FRAMING_BLOCKS, blocks_per_item=blocks_per_item)


@dataclass(frozen=True)
class Readout:
    """A distinguishable, budgeted readout awaiting render.

    ``item_blocks`` is the body: a flat list where each item occupies
    ``blocks_per_item`` blocks. ``identity_glyph`` is the readout's chosen glyph
    (D-2 design variable) — placed in the header on render.
    """

    header: str
    identity_glyph: str
    summary: str
    context_footer: str
    fallback_text: str
    item_blocks: list[Block]
    blocks_per_item: int = 1
    drill_pointer: str | None = None

    @property
    def total_items(self) -> int:
        return len(self.item_blocks) // self.blocks_per_item


@dataclass(frozen=True)
class RenderedReadout:
    """The posted artifact + the receipts that prove it is fit to post."""

    blocks: list[Block]
    text: str
    budget: bb.BudgetReceipt
    distinguishability: dist.DistinguishabilityReceipt
    identity_glyph: str = field(default="")

    @property
    def deliverable(self) -> bool:
        """Fit to post iff distinguishable AND within the hard block ceiling."""
        return self.distinguishability.distinguishable and self.budget.within_ceiling

    def delivery_receipt(
        self,
        *,
        invocation_id: str,
        channel: str,
        delivered_at: str,
        outcome: str = "readout",
        trace_id: str | None = None,
    ) -> DeliveryReceipt:
        """The EX-4-consumable delivery receipt for this exact rendered payload."""
        return DeliveryReceipt.for_payload(
            invocation_id=invocation_id,
            channel=channel,
            blocks=self.blocks,
            text=self.text,
            delivered_at=delivered_at,
            outcome=outcome,
            trace_id=trace_id,
        )


def render(
    readout: Readout,
    *,
    occupants: ChannelOccupants = DEFAULT_ACCOUNT_HEALTH_OCCUPANTS,
) -> RenderedReadout:
    """Render a ``Readout`` to blocks + text, applying the budget and duties.

    The rendered payload is complete-by-construction under the ceiling: overflow
    self-marks with ``:scissors:`` and complete counts. The two receipts are the
    proof the artifact is fit to post; nothing is sent.
    """
    budget = default_budget(readout.blocks_per_item)
    plan = bb.plan(budget, readout.total_items)

    shown_blocks = readout.item_blocks[: plan.shown_items * readout.blocks_per_item]

    blocks: list[Block] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{readout.identity_glyph} {readout.header}".strip(),
                "emoji": True,
            },
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": readout.summary}},
        {"type": "divider"},
        *shown_blocks,
    ]
    if plan.truncation_marker_present:
        blocks.append(
            bb.truncation_marker_block(
                plan.shown_items,
                plan.total_items,
                glyph=occupants.truncation_glyph,
                drill_pointer=readout.drill_pointer,
            )
        )
    blocks.append(
        {"type": "context", "elements": [{"type": "mrkdwn", "text": readout.context_footer}]}
    )

    distinguishability = dist.evaluate(
        blocks,
        readout.fallback_text,
        identity_glyph=readout.identity_glyph,
        occupants=occupants,
    )
    return RenderedReadout(
        blocks=blocks,
        text=readout.fallback_text,
        budget=plan,
        distinguishability=distinguishability,
        identity_glyph=readout.identity_glyph,
    )
