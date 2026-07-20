"""C6 honesty passthrough — two-sided (non-interference-attestation Points B & C).

Point C (permissible-null, MUST pass GREEN): faithful DISCLOSURE of the honesty
state passes — and ONLY faithful/more-honest disclosure passes.
Point B (stale-falsehood, MUST bite RED): a HIDING renderer (drops a field) and a
FABRICATING renderer (flips a flag toward reassurance) are BOTH rejected.
"""

from __future__ import annotations

import pytest
from asana_mcp.observability import (
    NATIVE_HONESTY_FIELDS,
    HonestySuppressionError,
    assert_honesty_passthrough,
)

FAITHFUL_UP = {
    "stale_served": True,
    "honest_empty": True,
    "contract_complete": False,
    "honest_contract_complete": False,
}


# --- GREEN (permissible-null): faithful disclosure passes ---
def test_faithful_passthrough_passes() -> None:
    assert_honesty_passthrough(dict(FAITHFUL_UP), dict(FAITHFUL_UP))  # no raise


# --- RED (teeth, hiding): dropping a field is rejected ---
def test_drop_honest_empty_rejected() -> None:
    surfaced = dict(FAITHFUL_UP)
    del surfaced["honest_empty"]
    with pytest.raises(HonestySuppressionError):
        assert_honesty_passthrough(dict(FAITHFUL_UP), surfaced)


# --- RED (teeth, fabrication): stale_served True->False hides staleness ---
def test_flip_stale_served_to_reassuring_rejected() -> None:
    surfaced = dict(FAITHFUL_UP)
    surfaced["stale_served"] = False
    with pytest.raises(HonestySuppressionError):
        assert_honesty_passthrough(dict(FAITHFUL_UP), surfaced)


# --- RED (teeth, fabrication): honest_empty True->False hides emptiness ---
def test_flip_honest_empty_rejected() -> None:
    surfaced = dict(FAITHFUL_UP)
    surfaced["honest_empty"] = False
    with pytest.raises(HonestySuppressionError):
        assert_honesty_passthrough(dict(FAITHFUL_UP), surfaced)


# --- RED (teeth, fabrication): contract_complete False->True fakes completeness ---
def test_flip_contract_complete_to_reassuring_rejected() -> None:
    surfaced = dict(FAITHFUL_UP)
    surfaced["contract_complete"] = True
    with pytest.raises(HonestySuppressionError):
        assert_honesty_passthrough(dict(FAITHFUL_UP), surfaced)


# --- GREEN (disclosure permitted): moving TOWARD more honesty is allowed ---
def test_move_toward_more_honesty_allowed() -> None:
    # upstream did not flag staleness; surfacing stale_served=True is MORE honest.
    assert_honesty_passthrough({"stale_served": False}, {"stale_served": True})  # no raise


# --- GREEN: fields absent upstream need not be surfaced ---
def test_absent_upstream_fields_ignored() -> None:
    assert_honesty_passthrough({"stale_served": True}, {"stale_served": True})  # no raise


# --- the field set IS the verified-native tuple (SVR-5) ---
def test_native_fields_are_the_verified_set() -> None:
    assert NATIVE_HONESTY_FIELDS == (
        "stale_served",
        "honest_empty",
        "contract_complete",
        "honest_contract_complete",
    )
