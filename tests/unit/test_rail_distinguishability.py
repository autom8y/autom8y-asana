"""Two-sided proofs for D-1..D-4 (EX-6 design limb).

Each duty has a positive control (distinguishable readout -> passes) and a
negative control (a readout that collides on exactly that surface -> that duty,
and only the joint verdict, fails). The teeth bite on substance, not shape.

Exit crit 1: D-1..D-4 are JOINTLY sufficient -- three-of-four is indistinguishable
at the surface it missed. Exit crit 2: D-4 is receipted at the FALLBACK TEXT
surface, never the desktop blocks.
"""

from __future__ import annotations

from autom8_asana.observability.rail_delivery.distinguishability import evaluate
from autom8_asana.observability.rail_delivery.occupants import (
    DEFAULT_ACCOUNT_HEALTH_OCCUPANTS as OCC,
)

DISTINCT_TEXT = "Weekly offers insight: 3 offers changed section this week."


def _blocks(
    header: str = ":bar_chart: Weekly Offers Insights",
    footer: str = "offers-insight | weekly readout",
    body: list[dict] | None = None,
) -> list[dict]:
    body = body or [{"type": "section", "text": {"type": "mrkdwn", "text": "3 offers moved"}}]
    return [
        {"type": "header", "text": {"type": "plain_text", "text": header, "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "5 of 22 sections"}},
        {"type": "divider"},
        *body,
        {"type": "context", "elements": [{"type": "mrkdwn", "text": footer}]},
    ]


# --- positive control ------------------------------------------------------


def test_distinguishable_readout_passes_all_four_jointly():
    receipt = evaluate(_blocks(), DISTINCT_TEXT)
    assert receipt.distinguishable is True
    assert receipt.missed_surfaces == ()
    assert [d.passed for d in receipt.duties] == [True, True, True, True]


# --- D-1 header ------------------------------------------------------------


def test_d1_fails_when_header_opens_like_incumbent():
    blocks = _blocks(header=":bar_chart: Account Status Reconciliation Weekly")
    receipt = evaluate(blocks, DISTINCT_TEXT)
    d1 = next(d for d in receipt.duties if d.duty == "D-1")
    assert d1.passed is False
    assert d1.surface == "header"
    assert d1.collided_with == "account status reconciliation"
    assert receipt.distinguishable is False
    assert "header" in receipt.missed_surfaces


def test_d1_passes_when_header_is_distinct():
    d1 = next(d for d in evaluate(_blocks(), DISTINCT_TEXT).duties if d.duty == "D-1")
    assert d1.passed is True


# --- D-2 identity glyph ----------------------------------------------------


def test_d2_fails_when_identity_glyph_is_reserved_alert():
    blocks = _blocks(header=":warning: Weekly Offers Insights")
    d2 = next(d for d in evaluate(blocks, DISTINCT_TEXT).duties if d.duty == "D-2")
    assert d2.passed is False
    assert d2.observed == ":warning:"


def test_d2_fails_when_alert_glyph_leaks_into_body_even_with_good_identity():
    body = [{"type": "section", "text": {"type": "mrkdwn", "text": ":warning: 3 at risk"}}]
    blocks = _blocks(header=":bar_chart: Weekly Offers Insights", body=body)
    d2 = next(d for d in evaluate(blocks, DISTINCT_TEXT).duties if d.duty == "D-2")
    assert d2.passed is False
    assert d2.collided_with == ":warning:"


def test_d2_fails_when_no_identity_glyph_chosen():
    blocks = _blocks(header="Weekly Offers Insights")  # no glyph anywhere
    d2 = next(d for d in evaluate(blocks, DISTINCT_TEXT).duties if d.duty == "D-2")
    assert d2.passed is False
    assert d2.observed is None


def test_d2_fails_when_identity_glyph_is_the_truncation_token():
    # A readout headed by :scissors: reads as a truncation, not a report.
    blocks = _blocks(header=":scissors: Weekly Offers Insights")
    d2 = next(d for d in evaluate(blocks, DISTINCT_TEXT).duties if d.duty == "D-2")
    assert d2.passed is False
    assert d2.observed == ":scissors:"


def test_d2_tolerates_scissors_on_a_non_header_truncation_marker():
    # :scissors: is the channel's truncation token; on a marker block (not the
    # header) it is rule-consistent and must NOT trip D-2.
    body = [
        {"type": "section", "text": {"type": "mrkdwn", "text": "item 1"}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": ":scissors: Showing 1 of 9"}]},
    ]
    blocks = _blocks(header=":bar_chart: Weekly Offers Insights", body=body)
    receipt = evaluate(blocks, DISTINCT_TEXT)
    d2 = next(d for d in receipt.duties if d.duty == "D-2")
    assert d2.passed is True
    assert d2.observed == ":bar_chart:"


# --- D-3 context footer ----------------------------------------------------


def test_d3_fails_when_footer_reuses_incumbent_producer():
    blocks = _blocks(footer="account-status-recon | readiness gate")
    d3 = next(d for d in evaluate(blocks, DISTINCT_TEXT).duties if d.duty == "D-3")
    assert d3.passed is False
    assert d3.collided_with == "account-status-recon | readiness gate"


def test_d3_passes_with_distinct_producer():
    d3 = next(d for d in evaluate(_blocks(), DISTINCT_TEXT).duties if d.duty == "D-3")
    assert d3.passed is True


# --- D-4 fallback text (the notification/mobile surface) -------------------


def test_d4_fails_at_the_text_surface_even_when_desktop_blocks_are_distinct():
    # THE exit-crit-2 teeth: blocks are perfectly distinguishable, but the
    # fallback text -- the only thing many readers see -- opens like the
    # incumbent. A desktop-blocks-only receipt would MISS this silent collision.
    colliding_text = "Account status reconciliation summary: 3 offers moved."
    receipt = evaluate(_blocks(), colliding_text)
    d4 = next(d for d in receipt.duties if d.duty == "D-4")
    assert d4.passed is False
    assert d4.surface == "fallback_text"
    assert d4.collided_with == "account status reconciliation"
    # and the joint verdict is False on the strength of the text surface alone
    assert receipt.distinguishable is False
    assert receipt.missed_surfaces == ("fallback_text",)


def test_d4_fails_when_fallback_text_is_empty():
    d4 = next(d for d in evaluate(_blocks(), "").duties if d.duty == "D-4")
    assert d4.passed is False


def test_d4_pass_receipt_attests_the_notification_surface_directly():
    d4 = next(d for d in evaluate(_blocks(), DISTINCT_TEXT).duties if d.duty == "D-4")
    assert d4.passed is True
    # the receipt itself records WHICH surface it inspected (not desktop blocks)
    assert "notification" in d4.detail
    assert "not" in d4.detail and "desktop blocks" in d4.detail


# --- joint sufficiency: three-of-four is NOT 75% -------------------------


def test_three_of_four_is_indistinguishable_not_seventy_five_percent():
    # Distinct header/glyph/footer (D-1/D-2/D-3 pass) but the notification line
    # collides (D-4 fails). Exactly three duties pass; the readout is NOT
    # distinguishable -- it is indistinguishable at the surface it missed.
    receipt = evaluate(_blocks(), "Account status reconciliation weekly digest")
    passed = [d.duty for d in receipt.duties if d.passed]
    missed = [d.duty for d in receipt.duties if not d.passed]
    assert passed == ["D-1", "D-2", "D-3"]
    assert missed == ["D-4"]
    assert receipt.distinguishable is False


def test_receipt_is_json_serialisable_with_per_duty_rows():
    d = evaluate(_blocks(), DISTINCT_TEXT).to_dict()
    assert d["distinguishable"] is True
    assert len(d["duties"]) == 4
    assert {row["duty"] for row in d["duties"]} == {"D-1", "D-2", "D-3", "D-4"}
    assert d["occupants_provenance"] == OCC.provenance
