"""The ONE canonical content-hash for a delivered readout payload — REC-001.

Chain-of-custody-closure CC-1. Before this module existed there were TWO
canonicalizations of "the readout payload":

  * generation-side ``content_hash_of(blocks)`` — hashed the blocks ALONE; and
  * delivery-side ``content_hash(blocks, text)`` — hashed ``{blocks, text}``.

They produced DIFFERENT digests for the same delivered artifact (the RED capture
recorded "two canonicalizations agree? False"). A swap-detector that compares a
generation-side digest to a delivery-side digest across that split can never
fire: the two sides disagree even on an HONEST delivery. So the swap-check had to
be grounded on one, and only one, canonicalization.

This module is that one canonicalization. Both the generation side
(``readout.generation``) and the delivery side
(``observability.rail_delivery.delivery_receipt``) import ``canonical_payload_hash``
and call it — there is no second ``json.dumps`` of the readout payload anywhere.
The chosen form is the delivery-side ``{blocks, text}`` shape, because a Slack
message IS ``blocks`` + a top-level fallback ``text``: hashing the blocks alone
would leave the fallback ``text`` unbound and a text-only swap invisible.

Canonicalization: JSON with sorted keys and no incidental whitespace, so
semantically-identical payloads hash identically and any content change — in a
block OR in the fallback text — flips the digest.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


def canonical_payload_hash(blocks: Sequence[Mapping[str, object]], text: str) -> str:
    """SHA-256 over the canonical bytes of a Slack readout payload ``{blocks, text}``.

    THE cross-sprint contract: the generation side (which sets
    ``report_generated.content_hash``) and the delivery side (which projects
    ``report_posted``'s ``content_hash``) MUST both bind the payload through
    THIS function, or the join's swap-check is meaningless.

    ``blocks`` is normalised to a list so any ``Sequence`` input yields the same
    bytes the wire form (``list[Block]``) produces; the two live call sites both
    already pass a list, so this is a no-op for them.
    """
    canonical = json.dumps(
        {"blocks": list(blocks), "text": text},
        sort_keys=True,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
