"""Two-sided proofs for the block budget + overflow (EX-6 design limb).

Exit crit 4: overflow is explicit and observable -- stay provably under budget OR
mark self-truncation; never silent. Exit crit 5: budget is per MESSAGE, not per
channel. RAILS…:643-708.
"""

from __future__ import annotations

import inspect

import pytest

from autom8_asana.observability.rail_delivery import block_budget as bb

# --- explicit budget: stated numbers, not emergent (exit crit 4) ----------


def test_item_ceiling_is_a_stated_derivation_bpi1():
    b = bb.BlockBudget(framing_blocks=4, blocks_per_item=1)
    # 50 - 10 reserved - 4 framing = 36 body; hold 1 for the marker => 35.
    assert b.available_body_blocks == 36
    assert b.item_ceiling == 35


def test_item_ceiling_tracks_blocks_per_item():
    b = bb.BlockBudget(framing_blocks=4, blocks_per_item=2)
    assert b.item_ceiling == (36 - 1) // 2  # == 17


def test_budget_rejects_impossible_inputs():
    with pytest.raises(ValueError):
        bb.BlockBudget(framing_blocks=4, blocks_per_item=0)
    with pytest.raises(ValueError):
        bb.BlockBudget(framing_blocks=100, blocks_per_item=1)  # framing > body budget


# --- under budget: complete, no marker -------------------------------------


def test_plan_under_ceiling_is_complete_and_unmarked():
    b = bb.BlockBudget(framing_blocks=4, blocks_per_item=1)
    r = bb.plan(b, total_items=10)
    assert r.shown_items == 10
    assert r.truncated is False
    assert r.truncation_marker_present is False
    assert r.complete is True
    assert r.rendered_block_total == 4 + 10  # framing + items
    assert r.within_ceiling is True


def test_plan_at_exactly_ceiling_does_not_truncate():
    b = bb.BlockBudget(framing_blocks=4, blocks_per_item=1)
    r = bb.plan(b, total_items=b.item_ceiling)
    assert r.truncated is False
    assert r.complete is True


# --- over budget: self-truncate, marked, still under the hard ceiling ------


def test_plan_over_ceiling_self_truncates_with_a_marker():
    b = bb.BlockBudget(framing_blocks=4, blocks_per_item=1)
    r = bb.plan(b, total_items=100)
    assert r.shown_items == b.item_ceiling == 35
    assert r.dropped_items == 65
    assert r.truncated is True
    assert r.truncation_marker_present is True  # NEVER silent
    assert r.complete is False
    assert r.rendered_block_total == 4 + 35 + 1  # framing + items + marker
    assert r.rendered_block_total <= bb.DEFAULT_MAX_BLOCKS
    assert r.within_ceiling is True


def test_truncation_is_never_silent_across_the_overflow_boundary():
    # The defect the incumbent already fixed: a truncated report with no marker.
    # Our plan must never produce truncated=True with marker=False.
    b = bb.BlockBudget(framing_blocks=4, blocks_per_item=1)
    for total in range(0, 120):
        r = bb.plan(b, total)
        if r.truncated:
            assert r.truncation_marker_present is True, f"silent truncation at {total}"
        assert r.complete == (r.dropped_items == 0)


def test_rendered_total_never_exceeds_the_hard_slack_ceiling():
    # Invariant fuzz: for any item count, the rendered message stays <= 50 blocks.
    for bpi in (1, 2, 3):
        b = bb.BlockBudget(framing_blocks=4, blocks_per_item=bpi)
        for total in range(0, 300):
            r = bb.plan(b, total)
            assert r.rendered_block_total <= bb.DEFAULT_MAX_BLOCKS
            assert r.within_ceiling is True


# --- per MESSAGE, not per channel (exit crit 5) ----------------------------


def test_budget_signature_has_no_channel_or_cotenant_input():
    # Co-tenancy and the ceiling are INDEPENDENT: the budget depends only on the
    # readout's OWN framing + items. Structurally, no channel/traffic parameter
    # may enter BlockBudget or plan().
    budget_fields = set(bb.BlockBudget.__dataclass_fields__)
    assert budget_fields == {"framing_blocks", "blocks_per_item", "max_blocks", "reserved_blocks"}
    plan_params = set(inspect.signature(bb.plan).parameters)
    assert plan_params == {"budget", "total_items"}
    for banned in ("channel", "cotenant", "co_tenant", "channel_traffic", "other_blocks"):
        assert banned not in budget_fields
        assert banned not in plan_params


def test_same_readout_budgets_identically_regardless_of_imagined_channel_load():
    b = bb.BlockBudget(framing_blocks=4, blocks_per_item=1)
    # Whatever else is posting to the channel, the readout's own plan is fixed.
    assert bb.plan(b, 20).to_dict() == bb.plan(b, 20).to_dict()


# --- the truncation marker: complete-by-counts, not by drill-out -----------


def test_truncation_marker_carries_complete_counts_and_scissors():
    block = bb.truncation_marker_block(5, 9)
    text = block["elements"][0]["text"]
    assert block["type"] == "context"
    assert text.startswith(":scissors:")
    assert "Showing 5 of 9" in text
    assert "counts above are complete" in text
    # completeness is carried by the counts, NOT a drill pointer (NF-1 404, S5)
    assert "Full detail:" not in text


def test_truncation_marker_appends_drill_pointer_only_when_given():
    block = bb.truncation_marker_block(5, 9, drill_pointer="https://x/latest")
    assert "Full detail: https://x/latest" in block["elements"][0]["text"]
