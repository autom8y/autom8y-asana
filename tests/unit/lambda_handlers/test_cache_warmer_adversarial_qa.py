"""QA-adversary probes for TD-005 bulk pre-materialization codec + coverage.

ADVERSARIAL tests (QA stream, not implementer) targeting:
  R4  the (gid:entity_type) token codec's colon assumption — what happens with
      a GID that CONTAINS a colon, and confirmation that EVERY real registry GID
      is numeric (codec-safe) so the assumption is grounded, not hoped.
  R4b partial-coverage (strict=False) reporting honesty — a zero/empty
      enumeration yields 0.0 coverage (not a fabricated 100%).
  R5  TD-005 leverages the registry's STATIC GID set; this probe documents the
      static-registry-vs-live-discovery coupling as a known boundary.
"""

from __future__ import annotations

import re

import pytest

from autom8_asana.lambda_handlers.cache_warmer import (
    _decode_key_token,
    _encode_key_token,
)

# --------------------------------------------------------------------------- #
# R4 — codec colon hazard + numeric-GID safety.
# --------------------------------------------------------------------------- #


def test_codec_roundtrips_numeric_gid() -> None:
    """Happy path: a numeric GID survives encode/decode intact."""
    token = _encode_key_token("1200653012566782", "section")
    assert token == "1200653012566782:section"
    assert _decode_key_token(token) == ("1200653012566782", "section")


def test_codec_corrupts_a_gid_containing_a_colon() -> None:
    """A GID with a colon is MIS-DECODED — split(':', 1) truncates it.

    This is the engineer-flagged failure mode. Encoding produces
    ``"12:34:section"``; decoding splits on the FIRST colon and returns
    ``("12", "34:section")`` — the GID is truncated and the entity_type is
    corrupted. We assert the corruption EXPLICITLY: the codec is only safe
    BECAUSE real GIDs are colon-free (proven by the numeric-safety test below).
    If a future GID source ever admitted a colon, this is the silent break.
    """
    poisoned_gid = "12:34"
    token = _encode_key_token(poisoned_gid, "section")
    decoded_gid, decoded_arm = _decode_key_token(token)

    assert (decoded_gid, decoded_arm) != (poisoned_gid, "section"), (
        "codec unexpectedly survived a colon in the GID"
    )
    assert decoded_gid == "12"
    assert decoded_arm == "34:section", "first-colon split corrupts the arm field"


def test_every_registry_gid_is_colon_free_and_numeric() -> None:
    """The codec assumption holds for EVERY enumerated bulk key.

    bulk_prematerialization_keys() is the only producer of codec inputs in
    production. If every (gid, arm) it yields has a numeric GID and a colon-free
    arm, the colon hazard above is unreachable in prod. This is the load-bearing
    safety proof for the codec's documented "GIDs are numeric" assumption.
    """
    from autom8_asana.core.project_registry import bulk_prematerialization_keys

    numeric = re.compile(r"^\d+$")
    for gid, arm in bulk_prematerialization_keys():
        assert numeric.match(gid), f"non-numeric GID would break the codec: {gid!r}"
        assert ":" not in gid, f"colon in GID would break the codec: {gid!r}"
        assert ":" not in arm, f"colon in arm would break the codec: {arm!r}"
        # Roundtrip must be lossless for every real key.
        assert _decode_key_token(_encode_key_token(gid, arm)) == (gid, arm)


def test_decode_rejects_token_with_no_colon() -> None:
    """A token missing the separator raises (no silent 1-tuple corruption)."""
    with pytest.raises(ValueError):
        _decode_key_token("no_separator_here")


# --------------------------------------------------------------------------- #
# R4b — coverage-rate honesty (zero denominator is not 100%).
# --------------------------------------------------------------------------- #


def test_coverage_rate_zero_denominator_is_zero_not_one() -> None:
    """emit_warmer_coverage_rate(0, 0) returns 0.0, not a fabricated 1.0.

    'Nothing enumerated' must not read as 'fully covered' (the TD-007 honesty
    theme applied to TD-005 coverage).
    """
    from autom8_asana.lambda_handlers.cloudwatch import emit_warmer_coverage_rate

    assert emit_warmer_coverage_rate(0, 0) == 0.0


def test_coverage_rate_partial_is_reported_honestly() -> None:
    """A partial warm (strict=False) reports the true fraction, not 1.0."""
    from autom8_asana.lambda_handlers.cloudwatch import emit_warmer_coverage_rate

    assert emit_warmer_coverage_rate(40, 46) == pytest.approx(40 / 46)
    assert emit_warmer_coverage_rate(46, 46) == 1.0


# --------------------------------------------------------------------------- #
# R5 — static-registry vs live-discovery coupling (documented boundary).
# --------------------------------------------------------------------------- #


def test_bulk_keys_are_driven_by_consumer_warm_set_not_live_discovery() -> None:
    """TD-005 / ADR-3: warms the CONSUMER-derived warm set, independent of live discovery.

    ADR-3 §3.1 (CF-3) corrected the prior coupling: the warm set is no longer the
    23 static DOMAIN-registry GIDs (which omitted 11 consumer-queried GIDs that
    then cold-503'd under bulk fan-out) but the 34-GID consumer subclass set. The
    static-vs-live correspondence the re-gate stream owns (VG-004) is now:
    ``consumer_warm_set_gids()`` must be a SUPERSET of the live
    ``refresh_frames`` enumeration. The domain ``_REGISTRY`` remains a strict
    SUBSET of the warm set (no resolution-behavior change for the 23).
    """
    from autom8_asana.core.project_registry import (
        _REGISTRY,
        bulk_prematerialization_keys,
        consumer_warm_set_gids,
    )

    warmed_gids = {gid for gid, _ in bulk_prematerialization_keys()}
    assert warmed_gids == set(consumer_warm_set_gids()), (
        "bulk warm set must equal the consumer-derived warm set (ADR-3)"
    )
    # Reconciled coverage is measured against the 34-GID consumer set.
    assert len(warmed_gids) == 34
    # Pure-additive: the 23 domain GIDs stay a strict subset of the warm set.
    assert set(_REGISTRY.values()) < warmed_gids
