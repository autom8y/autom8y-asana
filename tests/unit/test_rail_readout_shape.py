"""Integration proofs: the readout SHAPE composes distinguishability + budget.

The crucial compose test is that an OVERFLOWING readout self-marks with
:scissors: AND stays distinguishable -- the budget's truncation token does not
fight the D-2 glyph duty. Also proves the stated budget matches the actual render
(no drift) and that the delivery receipt is derived from the exact posted bytes.
"""

from __future__ import annotations

from autom8_asana.observability.rail_delivery.delivery_receipt import content_hash
from autom8_asana.observability.rail_delivery.readout import Readout, render


def _readout(
    header: str = "Weekly Offers Insights",
    glyph: str = ":bar_chart:",
    footer: str = "offers-insight | weekly readout",
    text: str = "Weekly offers insight: 3 offers changed section this week.",
    n_items: int = 10,
    bpi: int = 1,
    drill: str | None = None,
) -> Readout:
    items = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"item {i}"}}
        for i in range(n_items * bpi)
    ]
    return Readout(
        header=header,
        identity_glyph=glyph,
        summary="5 of 22 sections in scope",
        context_footer=footer,
        fallback_text=text,
        item_blocks=items,
        blocks_per_item=bpi,
        drill_pointer=drill,
    )


def test_distinct_under_budget_readout_is_deliverable():
    r = render(_readout(n_items=10))
    assert r.distinguishability.distinguishable is True
    assert r.budget.truncated is False
    assert r.deliverable is True
    # stated budget matches the actual render -- no drift
    assert len(r.blocks) == r.budget.rendered_block_total


def test_overflowing_readout_self_marks_and_stays_distinguishable():
    r = render(_readout(n_items=80))  # >> item_ceiling (35)
    assert r.budget.truncated is True
    assert r.budget.truncation_marker_present is True
    # the marker's :scissors: (a body block) does NOT trip D-2
    assert r.distinguishability.distinguishable is True
    # a :scissors: marker context block is present in the rendered output
    marker_texts = [
        el["text"]
        for b in r.blocks
        if b.get("type") == "context"
        for el in b.get("elements", [])
        if ":scissors:" in el.get("text", "")
    ]
    assert len(marker_texts) == 1
    assert "Showing 35 of 80" in marker_texts[0]
    # still fit to post: distinguishable AND within the hard ceiling
    assert r.deliverable is True
    assert len(r.blocks) == r.budget.rendered_block_total
    assert r.budget.rendered_block_total <= 50


def test_colliding_header_makes_readout_undeliverable():
    r = render(_readout(header="Account Status Reconciliation Weekly"))
    assert r.distinguishability.distinguishable is False
    assert "header" in r.distinguishability.missed_surfaces
    assert r.deliverable is False


def test_delivery_receipt_is_derived_from_the_exact_posted_payload():
    r = render(_readout(n_items=10))
    receipt = r.delivery_receipt(
        invocation_id="inv-42",
        channel="#account-health",
        delivered_at="2026-08-13T12:00:00Z",
    )
    assert receipt.block_count == len(r.blocks)
    assert receipt.content_hash == content_hash(r.blocks, r.text)


def test_render_accounting_holds_for_multi_block_items():
    r = render(_readout(n_items=50, bpi=2))  # 50 items * 2 blocks each -> overflow
    assert r.budget.truncated is True
    assert len(r.blocks) == r.budget.rendered_block_total
    assert r.budget.rendered_block_total <= 50
