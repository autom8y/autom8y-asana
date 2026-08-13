"""The item-1a readout generation mechanism.

EX-5 (WS-2). Assembles the recurring exec readout from a ``/rows`` response and
emits the ``report_generated`` provenance event that EX-4's ``GenerationReceipt``
contract consumes — the discharge site EX-4's NR-4 narrowed negative named
(``schema.py`` module docstring: "EX-5 (WS-2 generation mechanism) is the
discharge site").

The mechanism is a pure function ``render(response, ...) -> GeneratedOccurrence``
plus the ``report_generated`` event it emits. No human types any slot: the
``report_generated`` event carries ``assembled_by="machine"`` and
``human_in_loop=False`` UNCONDITIONALLY — the mechanism cannot emit a human
authorship, which is the load-bearing "no human assembled it" claim (RUNG 2 limb
(a)). Emitting a hand-assembled brief and calling it rung 2 is the founding-wound
anti-pattern this initiative exists to end; the mechanism forecloses it by
construction.

EX-4 CONCERN-1 discharge — the REAL content_hash (REC-001)
----------------------------------------------------------
This mechanism emits a REAL ``content_hash`` binding the delivered artifact to
the machine-authored one. It is computed by the ONE shared canonicalization
``observability.payload_hash.canonical_payload_hash(blocks, text)`` — the SAME
symbol the delivery side (``rail_delivery.delivery_receipt``) calls. Before CC-1
the generation side hashed the blocks ALONE while delivery hashed
``{blocks, text}``; the two digests disagreed even for an honest delivery, so the
swap-check could never fire. Grounding BOTH sides on one canonicalization is
REC-001; the ``text`` half is the D-4 fallback surface (``render_fallback_text``).
The hash is a pure function of the bytes: identical ``{blocks, text}`` payload ->
identical hash; any change in a block OR the fallback text flips it. Once the
delivery emitter carries this same hash, the join compares the two digests
directly (join clause 4a); ``block_count`` (join clause 4b) remains a coarser
fallback for deliveries that carry no hash.

DF-1 — this module reads ONLY the ``/rows`` response bytes. It imports NOTHING
from ``query.temporal`` (``TemporalFilter``), ``section_timelines``, or the story
cache. Its only intra-repo imports are the item-1a computation, the template,
and EX-4's frozen event/enum names (so the emission stays in lockstep with the
contract it must satisfy).

CR-1 — the mechanism READS offer rows (via the response bytes handed in) and its
delivered artifact posts to Slack (autonomous delivery, R-7). It performs NO
Asana write. This module fires no live/authenticated call: it is a pure function
over an in-memory response and emits an in-memory event; delivery is the caller's.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from autom8_asana.observability.payload_hash import canonical_payload_hash
from autom8_asana.observability.rung_receipts.schema import (
    GENERATION_EVENT,
    Assembler,
)
from autom8_asana.readout.item_1a import (
    G4PrimeBound,
    Item1aError,
    Item1aFigure,
    compute_item_1a,
    enumerate_g4_prime,
)
from autom8_asana.readout.template import (
    Ex2Disposition,
    render_blocks,
    render_fallback_text,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

# Machine generator identity carried on every ``report_generated`` event.
GENERATOR_NAME = "autom8_asana.readout.generation"
GENERATOR_VERSION = "ex5.item1a.v1"

# The mechanism NEVER emits a human authorship — RUNG 2 limb (a)'s load-bearing
# invariant. These are module constants, not parameters, so no call site can
# quietly flip them.
ASSEMBLED_BY = Assembler.MACHINE
HUMAN_IN_LOOP = False


@dataclass(frozen=True)
class GeneratedOccurrence:
    """One machine-generated readout occurrence: the artifact + its provenance.

    * ``blocks`` — the assembled block payload (delivered to Slack).
    * ``text`` — the D-4 fallback text of the Slack payload (``render_fallback_text``).
      The delivered artifact is ``{blocks, text}``; both are hashed together.
    * ``content_hash`` — SHA-256 over the canonical bytes of ``{blocks, text}`` via
      the ONE shared canonicalization (REC-001, ``canonical_payload_hash``). It
      matches the delivery side's hash for the SAME ``{blocks, text}`` — that
      agreement is what lets the join's clause-4a swap-check fire.
    * ``report_generated`` — the event dict EX-4's ``GenerationReceipt`` consumes,
      keyed on ``invocation_id`` and carrying the REAL ``content_hash``.
    """

    invocation_id: str
    seq: int
    figure: Item1aFigure
    g4_bound: G4PrimeBound
    blocks: list[dict[str, object]]
    text: str
    content_hash: str
    block_count: int
    report_generated: dict[str, object]


def extract_rows_and_meta(
    response: Mapping[str, object],
) -> tuple[list[Mapping[str, object]], Mapping[str, object] | None]:
    """Pull rows + meta out of a ``/rows`` response, double-envelope or flat.

    Accepts the canonical double-envelope ``{"data": {"data": [...], "meta":
    {...}}}`` (SuccessResponse[RowsResponse], models.py:523-557) or a flat
    ``RowsResponse`` ``{"data": [...], "meta": {...}}``. Binds to the response
    BYTES only — never a pydantic model — so the mechanism stays a pure function
    of the served bytes (DF-1 constraint 4).
    """
    data = response.get("data")
    if isinstance(data, dict):
        inner = data.get("data")
        meta = data.get("meta")
        if isinstance(inner, list):
            rows: list[Mapping[str, object]] = [r for r in inner if isinstance(r, dict)]
            return rows, meta if isinstance(meta, dict) else None
    if isinstance(data, list):
        flat_rows: list[Mapping[str, object]] = [r for r in data if isinstance(r, dict)]
        flat_meta = response.get("meta")
        return flat_rows, flat_meta if isinstance(flat_meta, dict) else None
    raise Item1aError(
        "unrecognised /rows response shape: expected a double-envelope "
        "{'data': {'data': [...], 'meta': {...}}} or a flat "
        "{'data': [...], 'meta': {...}}"
    )


def render(
    response: Mapping[str, object],
    *,
    cadence_label: str,
    seq: int,
    invocation_id: str,
    source_query_id: str,
    generated_at: str,
    in_scope_sections: Sequence[str],
    ex2_disposition: Ex2Disposition = Ex2Disposition.STILL_ONE,
) -> GeneratedOccurrence:
    """Generate one readout occurrence from a ``/rows`` response.

    The single entry point. Computes item 1a (DR-2 min floor), enumerates its
    per-render G4' bound (including the F-2 truncation branch), assembles the
    block payload, hashes it, and emits the ``report_generated`` event.

    Args:
        response: a ``POST /v1/query/offer/rows`` response (synthetic in this
            build; a real call is EXIT-HELD and operator/credential-gated).
        cadence_label: ruled-cadence label ("Weekly" recommended, Q-2 operator).
        seq: occurrence ordinal (join key).
        invocation_id: the join key EX-4's receipt binds delivery to generation.
        source_query_id: the ``/rows`` query id, recorded on the receipt.
        generated_at: generation instant, ISO-8601 UTC.
        in_scope_sections: the request's declared in-scope sections (``n``).
        ex2_disposition: EX-2's disposition for the extension point.

    Returns:
        A ``GeneratedOccurrence`` carrying the blocks and the ``report_generated``
        event with a REAL ``content_hash``.
    """
    rows, meta = extract_rows_and_meta(response)
    figure = compute_item_1a(rows, in_scope_sections, meta)
    g4_bound = enumerate_g4_prime(figure)
    blocks = render_blocks(
        figure=figure,
        g4_bound=g4_bound,
        cadence_label=cadence_label,
        seq=seq,
        generated_at=generated_at,
        ex2_disposition=ex2_disposition,
    )
    text = render_fallback_text(
        figure,
        cadence_label=cadence_label,
        seq=seq,
        generated_at=generated_at,
    )
    # REC-001: the ONE shared canonicalization over {blocks, text}. The delivery
    # side hashes the SAME {blocks, text} through the SAME symbol, so an honest
    # delivery's hash equals this one and the join's clause-4a swap-check can fire.
    content_hash = canonical_payload_hash(blocks, text)
    block_count = len(blocks)

    report_generated: dict[str, object] = {
        "event": GENERATION_EVENT,
        "invocation_id": invocation_id,
        "assembled_by": ASSEMBLED_BY.value,
        "human_in_loop": HUMAN_IN_LOOP,
        "generator": GENERATOR_NAME,
        "generator_version": GENERATOR_VERSION,
        "source_query_id": source_query_id,
        "content_hash": content_hash,
        "block_count": block_count,
        "generated_at": generated_at,
    }

    return GeneratedOccurrence(
        invocation_id=invocation_id,
        seq=seq,
        figure=figure,
        g4_bound=g4_bound,
        blocks=blocks,
        text=text,
        content_hash=content_hash,
        block_count=block_count,
        report_generated=report_generated,
    )
