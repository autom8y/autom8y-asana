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


def test_bulk_keys_are_driven_by_static_registry_not_live_discovery() -> None:
    """TD-005 warms the STATIC registry GID set, independent of live discovery.

    This pins the coupling the re-gate stream must own: the warm set is the
    23 static registry GIDs, NOT the GIDs the running receiver resolves from live
    workspace discovery (EntityProjectRegistry). If the live receiver serves a
    project GID that is NOT in this static set, that key is NEVER pre-warmed and
    will cold-build (503) under bulk fan-out — regardless of warmer_coverage_rate
    reporting 100% over the static set. This is a real-data correspondence check
    the unit layer cannot make; flagged here so it is not assumed away.
    """
    from autom8_asana.core.project_registry import (
        _REGISTRY,
        bulk_prematerialization_keys,
    )

    warmed_gids = {gid for gid, _ in bulk_prematerialization_keys()}
    assert warmed_gids == set(_REGISTRY.values()), (
        "bulk warm set must equal the static registry GID set"
    )
    # Coverage is measured against the static enumeration only — make that explicit.
    assert len(warmed_gids) == 23
