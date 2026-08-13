"""Proofs for the delivery-receipt shape EX-4 consumes (EX-6 exit crit 6).

The load-bearing property is CONCERN-1: the receipt carries a real content_hash
so EX-4's swap-check (delivery.content_hash == generation.content_hash) can fire.
"""

from __future__ import annotations

from autom8_asana.observability.rail_delivery.delivery_receipt import (
    DELIVERY_RECEIPT_JSON_SCHEMA,
    DeliveryReceipt,
    content_hash,
    content_hash_matches,
)

# EX-4 DeliveryReceipt fields (schema.py:172-179) -- the wire shape we must match.
EX4_DELIVERY_FIELDS = {
    "invocation_id",
    "channel",
    "block_count",
    "delivered_at",
    "outcome",
    "trace_id",
    "message_ts",
    "permalink",
}

BLOCKS = [
    {"type": "header", "text": {"type": "plain_text", "text": ":bar_chart: Insights"}},
    {"type": "section", "text": {"type": "mrkdwn", "text": "3 offers moved"}},
]
TEXT = "Weekly offers insight: 3 offers moved."


# --- content_hash: deterministic and sensitive ----------------------------


def test_content_hash_is_deterministic_and_prefixed():
    h = content_hash(BLOCKS, TEXT)
    assert h == content_hash(BLOCKS, TEXT)
    assert h.startswith("sha256:")


def test_content_hash_flips_on_any_block_change():
    other = [*BLOCKS[:1], {"type": "section", "text": {"type": "mrkdwn", "text": "4 offers moved"}}]
    assert content_hash(BLOCKS, TEXT) != content_hash(other, TEXT)


def test_content_hash_flips_on_text_change():
    assert content_hash(BLOCKS, TEXT) != content_hash(BLOCKS, TEXT + " (edited)")


# --- receipt derives block_count + content_hash from the payload -----------


def test_receipt_for_payload_derives_hash_and_count():
    r = DeliveryReceipt.for_payload(
        invocation_id="inv-1",
        channel="#account-health",
        blocks=BLOCKS,
        text=TEXT,
        delivered_at="2026-08-13T12:00:00Z",
    )
    assert r.block_count == len(BLOCKS)
    assert r.content_hash == content_hash(BLOCKS, TEXT)
    assert r.outcome == "readout"


# --- CONCERN-1: the swap-check EX-4 cannot make today ----------------------


def test_matching_payload_passes_the_swap_check():
    gen_hash = content_hash(BLOCKS, TEXT)  # what EX-5's report_generated would set
    delivery = DeliveryReceipt.for_payload(
        invocation_id="inv-1",
        channel="#account-health",
        blocks=BLOCKS,
        text=TEXT,
        delivered_at="2026-08-13T12:00:00Z",
    )
    assert content_hash_matches(delivery, gen_hash) is True


def test_swapped_payload_fails_the_swap_check():
    # Generation assembled BLOCKS; a different payload was delivered. Without a
    # delivery-side content_hash (EX-4 today) this swap is invisible; with it, it
    # cannot pass.
    gen_hash = content_hash(BLOCKS, TEXT)
    swapped = [{"type": "section", "text": {"type": "mrkdwn", "text": "hand-pasted"}}]
    delivery = DeliveryReceipt.for_payload(
        invocation_id="inv-1",
        channel="#account-health",
        blocks=swapped,
        text="hand-pasted summary",
        delivered_at="2026-08-13T12:00:00Z",
    )
    assert content_hash_matches(delivery, gen_hash) is False


# --- wire-shape compatibility with EX-4 ------------------------------------


def test_to_dict_is_ex4_fields_plus_content_hash():
    r = DeliveryReceipt.for_payload(
        invocation_id="inv-1",
        channel="#account-health",
        blocks=BLOCKS,
        text=TEXT,
        delivered_at="2026-08-13T12:00:00Z",
        trace_id="t-1",
    )
    keys = set(r.to_dict())
    assert keys == EX4_DELIVERY_FIELDS | {"content_hash"}


def test_json_schema_requires_content_hash_and_matches_ex4_shape():
    props = set(DELIVERY_RECEIPT_JSON_SCHEMA["properties"])
    assert props == EX4_DELIVERY_FIELDS | {"content_hash"}
    assert "content_hash" in DELIVERY_RECEIPT_JSON_SCHEMA["required"]
    # outcome enum mirrors EX-4 DeliveryOutcome values
    assert DELIVERY_RECEIPT_JSON_SCHEMA["properties"]["outcome"]["enum"] == [
        "readout",
        "abort",
        "other",
    ]
