"""Substrate-v2 424 data-integrity refusal classification (DP-3 §Ratification sequencing).

ADDITIVE + INERT consumer-side classification landed WITH-OR-BEFORE the server flip
(DP-3 hard sequencing, 2026-07-29). A 424 Failed Dependency from the (future) v2 serve
seam means "the substrate refused an unprovable number" — a data-integrity refusal that
is NON-retryable as a hot loop (the 429-scar-tissue concern) yet honors Retry-After
(the rebuild schedule). No current satellite surface emits 424, so this branch is dead
until v2 flips.

Two-sided teeth: the 424 branch fires with the right classification AND the pre-existing
generic-4xx (`client`) and 503-warming branches are UNDISTURBED (the edit is purely
additive — a new status intercept before the generic 4xx, changing nothing that flows
today).
"""

from __future__ import annotations

import httpx
from asana_mcp.errors import map_http_error


def test_424_is_a_non_retryable_data_integrity_refusal() -> None:
    err = map_http_error(
        httpx.Response(
            424,
            json={
                "error": {
                    "code": "SUBSTRATE_REFUSED_STALE",
                    "message": "plane v2/offer is 14d stale",
                }
            },
        )
    )
    assert err.kind == "data-integrity-refusal"
    assert err.retryable is False  # do NOT hot-retry (429-scar-tissue)
    assert err.status == 424
    assert err.code == "SUBSTRATE_REFUSED_STALE"
    # NOT mistaken for auth or warming — the disambiguation the C3 scar demands.
    assert "NOT an auth" in err.message
    assert "data-integrity refusal" in err.message
    assert "asana substrate" in err.message  # F-4: substrate-marked → substrate-asserting text
    # the substrate's own diagnosis is carried through (not flattened).
    assert "plane v2/offer is 14d stale" in err.message


def test_424_without_the_substrate_marker_gets_a_generic_message_not_a_false_substrate_claim() -> (
    None
):
    """F-4: a NON-substrate 424 (no SUBSTRATE_REFUSED_ code) is still classified data-integrity-
    refusal / non-retryable (424 = dependency-unprovable for ANY dependency — the safe default),
    but the message does NOT falsely assert 'asana substrate refused' (the WEBDAV-probe fix)."""
    err = map_http_error(httpx.Response(424, json={"error": {"code": "WEBDAV_LOCK_FAILED"}}))
    assert err.kind == "data-integrity-refusal"  # classification stays (no under-classification)
    assert err.retryable is False
    assert "asana substrate" not in err.message  # no false substrate attribution
    assert "upstream dependency" in err.message  # generic failed-dependency message
    assert err.code == "WEBDAV_LOCK_FAILED"  # the true upstream code is still carried


def test_424_honors_retry_after_header_bound_to_rebuild_schedule() -> None:
    err = map_http_error(httpx.Response(424, headers={"Retry-After": "180"}))
    assert err.kind == "data-integrity-refusal"
    assert err.retry_after == 180.0  # points the consumer at the rebuild schedule
    assert err.retryable is False  # the distinctive combo: wait-for-rebuild, do not loop


def test_424_reads_retry_after_from_the_body_details() -> None:
    err = map_http_error(
        httpx.Response(
            424,
            json={
                "error": {"code": "SUBSTRATE_REFUSED_MISSING"},
                "details": {"retry_after_seconds": 90},
            },
        )
    )
    assert err.kind == "data-integrity-refusal"
    assert err.retry_after == 90.0


def test_424_without_retry_after_is_still_classified() -> None:
    err = map_http_error(httpx.Response(424))
    assert err.kind == "data-integrity-refusal"
    assert err.retryable is False
    assert err.retry_after is None


# --- the OTHER side of the teeth: pre-existing branches are UNDISTURBED (additive) ---


def test_generic_4xx_still_maps_to_client_not_data_integrity() -> None:
    """A non-424 4xx keeps its `client` classification — the 424 intercept is additive."""
    err = map_http_error(httpx.Response(400, json={"error": {"code": "BAD_REQUEST"}}))
    assert err.kind == "client"
    assert err.kind != "data-integrity-refusal"


def test_503_warming_is_unchanged_by_the_424_branch() -> None:
    err = map_http_error(httpx.Response(503, json={"error": {"code": "CACHE_NOT_WARMED"}}))
    assert err.kind == "warming"
    assert err.retryable is True  # warming is still retryable — only 424 is the non-retry refusal
