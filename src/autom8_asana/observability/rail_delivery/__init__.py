"""Rail delivery + distinguishability — EX-6 design limb of exec-insight-delivery.

Makes a recurring readout *distinguishable* in a channel it shares with an alert
stream (D-1..D-4), fits it under a ceiling that truncates silently (block budget
+ explicit overflow), and emits a delivery-receipt shape EX-4's join consumes
(carrying ``content_hash``, closing EX-4 CONCERN-1).

Scope: DESIGN LIMB. Everything here is provable against the SHAPE of a readout
with synthetic block payloads. Nothing posts to Slack. The live wiring into the
ASR service is a monorepo change (out of scope for this PR) and the Phase-3
receipt limb (UV-P-C-3) needs EX-5's real payload.

See ``.ledge/decisions/RAILS-insight-delivery-verified-2026-08-12.md`` §5-§6 and
``.sos/wip/frames/exec-insight-delivery.shape.md`` §EX-6.
"""

from __future__ import annotations

from autom8_asana.observability.rail_delivery.block_budget import (
    DEFAULT_MAX_BLOCKS,
    DEFAULT_RESERVED_BLOCKS,
    TRUNCATION_GLYPH,
    BlockBudget,
    BudgetReceipt,
    plan,
    truncation_marker_block,
)
from autom8_asana.observability.rail_delivery.delivery_receipt import (
    DELIVERY_RECEIPT_JSON_SCHEMA,
    DeliveryReceipt,
    content_hash,
    content_hash_matches,
)
from autom8_asana.observability.rail_delivery.distinguishability import (
    DistinguishabilityReceipt,
    DutyReceipt,
    check_d1_header,
    check_d2_glyph,
    check_d3_footer,
    check_d4_fallback_text,
    evaluate,
)
from autom8_asana.observability.rail_delivery.occupants import (
    DEFAULT_ACCOUNT_HEALTH_OCCUPANTS,
    ChannelOccupants,
)
from autom8_asana.observability.rail_delivery.readout import (
    FRAMING_BLOCKS,
    Readout,
    RenderedReadout,
    default_budget,
    render,
)

__all__ = [
    # Channel-occupant registry.
    "ChannelOccupants",
    "DEFAULT_ACCOUNT_HEALTH_OCCUPANTS",
    # Distinguishability duties and receipts.
    "DutyReceipt",
    "DistinguishabilityReceipt",
    "evaluate",
    "check_d1_header",
    "check_d2_glyph",
    "check_d3_footer",
    "check_d4_fallback_text",
    # Block budget and overflow.
    "BlockBudget",
    "BudgetReceipt",
    "plan",
    "truncation_marker_block",
    "DEFAULT_MAX_BLOCKS",
    "DEFAULT_RESERVED_BLOCKS",
    "TRUNCATION_GLYPH",
    # Delivery receipt, carrying content_hash for the EX-4 join.
    "DeliveryReceipt",
    "content_hash",
    "content_hash_matches",
    "DELIVERY_RECEIPT_JSON_SCHEMA",
    # Readout shape.
    "Readout",
    "RenderedReadout",
    "render",
    "default_budget",
    "FRAMING_BLOCKS",
]
