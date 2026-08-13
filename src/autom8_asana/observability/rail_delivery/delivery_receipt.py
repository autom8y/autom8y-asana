"""Delivery-receipt shape EX-4's join consumes — carrying a real ``content_hash``.

EX-6 design limb (shape §EX-6 exit crit 6: "a delivery receipt shape that EX-4's
schema consumes — the two sprints meet here").

Why content_hash (EX-4 CONCERN-1)
---------------------------------
EX-4's ``rung_receipts`` join binds a *generation* receipt to a *delivery*
receipt on ``invocation_id`` so limb (a) can attest "no human assembled the
delivered payload". EX-4's ``GenerationReceipt`` carries a ``content_hash`` whose
stated job is to "bind the generated artifact to the delivered one so a swap
cannot pass" (EX-4 ``schema.py`` GenerationReceipt docstring). But EX-4's
``DeliveryReceipt`` (projected from the live ``report_posted`` event) carries NO
``content_hash`` — so the swap-check has only one side of the pair and cannot
actually fire. That is CONCERN-1.

This delivery receipt closes it: it mirrors EX-4's ``report_posted`` /
``DeliveryReceipt`` wire shape field-for-field AND adds ``content_hash``, computed
over the actual delivered payload by the SAME canonical function the generation
side must use. With both halves carrying the hash, EX-4's join can assert
``delivery.content_hash == generation.content_hash`` and a swapped payload cannot
pass.

Coordination note (does NOT edit EX-4)
--------------------------------------
EX-4's ``RUNG_E_LIMB_A_RECEIPT_JSON_SCHEMA`` ``delivery`` sub-object should gain
``content_hash`` (type string) to consume this field. That edit is EX-4's /
observability-engineer's to make on the receipt limb; this module provides the
field, the canonical hash function, and the swap-check so the two meet cleanly.
This module does NOT modify EX-4's frozen schema.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

# Mirrors EX-4 DeliveryOutcome values (schema.py:99-101). Kept as bare strings
# so this module carries no import dependency on EX-4's not-yet-in-tree package.
OUTCOME_READOUT = "readout"
OUTCOME_ABORT = "abort"
OUTCOME_OTHER = "other"

# The delivery event this receipt is projected from, in ASR. LIVE today
# (EX-4 schema.py:150 DELIVERY_EVENT). Named here for cross-sprint legibility.
DELIVERY_EVENT = "report_posted"

# A Slack Block Kit block; heterogeneous values -> ``object`` element type.
Block = dict[str, object]


def content_hash(blocks: list[Block], text: str) -> str:
    """Canonical content hash of a Slack payload — THE cross-sprint contract.

    Both the generation side (EX-5, which sets ``report_generated.content_hash``)
    and the delivery side (this receipt) MUST hash the payload this way, or the
    swap-check is meaningless. Canonicalisation: JSON with sorted keys and no
    incidental whitespace, so semantically-identical payloads hash identically
    and any content change flips the hash.
    """
    canonical = json.dumps(
        {"blocks": blocks, "text": text},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DeliveryReceipt:
    """EX-4 ``report_posted`` wire shape + ``content_hash`` (CONCERN-1)."""

    invocation_id: str
    channel: str
    block_count: int
    delivered_at: str
    outcome: str  # OUTCOME_READOUT | OUTCOME_ABORT | OUTCOME_OTHER
    content_hash: str  # <-- the CONCERN-1 field EX-4's DeliveryReceipt lacks
    trace_id: str | None = None
    message_ts: str | None = None
    permalink: str | None = None

    @staticmethod
    def for_payload(
        *,
        invocation_id: str,
        channel: str,
        blocks: list[Block],
        text: str,
        delivered_at: str,
        outcome: str = OUTCOME_READOUT,
        trace_id: str | None = None,
        message_ts: str | None = None,
        permalink: str | None = None,
    ) -> DeliveryReceipt:
        """Build a receipt from the payload actually posted.

        ``block_count`` and ``content_hash`` are derived from the payload so they
        cannot drift from what went on the wire.
        """
        return DeliveryReceipt(
            invocation_id=invocation_id,
            channel=channel,
            block_count=len(blocks),
            delivered_at=delivered_at,
            outcome=outcome,
            content_hash=content_hash(blocks, text),
            trace_id=trace_id,
            message_ts=message_ts,
            permalink=permalink,
        )

    def to_dict(self) -> dict[str, object]:
        """EX-4-compatible wire form (all EX-4 fields) plus ``content_hash``."""
        return {
            "invocation_id": self.invocation_id,
            "channel": self.channel,
            "block_count": self.block_count,
            "delivered_at": self.delivered_at,
            "outcome": self.outcome,
            "content_hash": self.content_hash,
            "trace_id": self.trace_id,
            "message_ts": self.message_ts,
            "permalink": self.permalink,
        }


def content_hash_matches(delivery: DeliveryReceipt, generation_content_hash: str) -> bool:
    """The swap-check EX-4's join performs once delivery carries the hash.

    True iff the delivered payload is byte-for-byte the generated one. A swapped
    or hand-edited payload flips the hash and this returns False — which is
    exactly the guarantee CONCERN-1 says EX-4 cannot make today.
    """
    return delivery.content_hash == generation_content_hash


# Portable wire contract for the delivery half, kept in the SAME shape as EX-4's
# RUNG_E_LIMB_A_RECEIPT_JSON_SCHEMA.delivery sub-object, with content_hash added.
# EX-4 / observability-engineer splices content_hash into the frozen schema; this
# fragment is the exact addition, not an edit to EX-4's file.
DELIVERY_RECEIPT_JSON_SCHEMA: dict[str, object] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://autom8y.dev/schemas/rail-delivery-receipt.json",
    "title": "Rail delivery receipt (EX-4 report_posted shape + content_hash)",
    "type": "object",
    "required": [
        "invocation_id",
        "channel",
        "block_count",
        "delivered_at",
        "outcome",
        "content_hash",
    ],
    "properties": {
        "invocation_id": {"type": "string"},
        "channel": {"type": "string"},
        "block_count": {"type": "integer"},
        "delivered_at": {"type": "string"},
        "outcome": {"enum": ["readout", "abort", "other"]},
        # The CONCERN-1 field. Format "sha256:<hex>" from content_hash().
        "content_hash": {"type": "string"},
        "trace_id": {"type": ["string", "null"]},
        "message_ts": {"type": ["string", "null"]},
        "permalink": {"type": ["string", "null"]},
    },
    "additionalProperties": False,
}
