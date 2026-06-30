"""Tests for the PURE scheduling-stratum resolver (Phase-2 normalizer-seam).

Locks: first-non-empty cascade ordering (each of the eight wins when it is first),
the all-empty -> inactive terminal, the GHL fail-closed coordinate carry, the
TrackStat/Sked URL formatters and ``build_ghl_url`` (monolith parity), the
``derive_effective_ghl_id`` empty-fallback precedence, and the SOURCE_TO_STRATUM
drift guard against the Phase-1 enum.
"""

from __future__ import annotations

import pytest

from autom8_asana.normalizer.scheduling_stratum import (
    CASCADE_PRIORITY,
    GHL_PREFIX,
    GHL_PREFIX_ALT,
    INACTIVE_STRATUM,
    SKED_PREFIX,
    SOURCE_TO_STRATUM,
    TRACKSTAT_PREFIX,
    StratumResult,
    build_ghl_url,
    derive_effective_ghl_id,
    format_sked_url,
    format_trackstat_url,
    resolve_stratum,
)

pytestmark = [pytest.mark.xdist_group("scheduling_normalizer")]

# The Phase-1 SchedulingStratumEnum member set (autom8y-data PR #218). Replicated
# here as the drift guard target -- if the resolver's stratum vocabulary drifts from
# this set the contract-match breaks.
_PHASE1_STRATUM_ENUM = {
    "reviewwave",
    "acuity",
    "calendly",
    "janeapp",
    "ehr",
    "trackstat",
    "sked",
    "ghl",
    "inactive",
}


def _empty_inputs() -> dict[str, str | None]:
    return {field: None for field in CASCADE_PRIORITY}


@pytest.mark.parametrize(
    ("winning_field", "expected_stratum"),
    [
        ("reviewwave_id", "reviewwave"),
        ("acuity_cal_url", "acuity"),
        ("calendly_url", "calendly"),
        ("janeapp_url", "janeapp"),
        ("ehr_cal_url", "ehr"),
        ("trackstat_id", "trackstat"),
        ("sked_id", "sked"),
        ("custom_ghl_id", "ghl"),
    ],
)
def test_each_source_wins_when_first_non_empty(winning_field: str, expected_stratum: str) -> None:
    """Each source field selects its stratum when it is the first non-empty in cascade."""
    inputs = _empty_inputs()
    # Populate ONLY the fields from the winner onward-empty earlier ones so the
    # winner is genuinely the first non-empty in priority order.
    win_idx = CASCADE_PRIORITY.index(winning_field)
    for field in CASCADE_PRIORITY[win_idx:]:
        inputs[field] = f"value-for-{field}"

    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.stratum == expected_stratum


def test_cascade_priority_earlier_wins_over_later() -> None:
    """An earlier source outranks a later one when both are present."""
    inputs = _empty_inputs()
    inputs["reviewwave_id"] = "rw-123"
    inputs["acuity_cal_url"] = "https://app.acuityscheduling.com/x"
    inputs["custom_ghl_id"] = "ghl-999"

    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.stratum == "reviewwave"


def test_all_empty_is_inactive() -> None:
    """All eight empty -> inactive, with no GHL coordinates."""
    result = resolve_stratum(_empty_inputs(), CASCADE_PRIORITY)
    assert result == StratumResult(
        stratum=INACTIVE_STRATUM, custom_ghl_id=None, ghl_calendar_id=None
    )


def test_whitespace_only_counts_as_empty() -> None:
    """A whitespace-only Asana text value does not win the cascade."""
    inputs = _empty_inputs()
    inputs["reviewwave_id"] = "   "
    inputs["acuity_cal_url"] = "https://app.acuityscheduling.com/x"
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.stratum == "acuity"


def test_ghl_coordinates_carried_for_non_ghl_stratum() -> None:
    """A non-GHL winner still carries the GHL fail-closed fallback coordinates."""
    inputs = _empty_inputs()
    inputs["acuity_cal_url"] = "https://app.acuityscheduling.com/x"
    inputs["custom_ghl_id"] = "cal-abc"

    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.stratum == "acuity"
    assert result.custom_ghl_id == "cal-abc"
    assert result.ghl_calendar_id == f"{GHL_PREFIX}/cal-abc"


def test_ghl_terminal_derives_url() -> None:
    """custom_ghl_id as the sole signal -> ghl stratum + derived booking URL."""
    inputs = _empty_inputs()
    inputs["custom_ghl_id"] = "cal-xyz"
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result == StratumResult(
        stratum="ghl",
        custom_ghl_id="cal-xyz",
        ghl_calendar_id=f"{GHL_PREFIX}/cal-xyz",
    )


def test_custom_ghl_id_whitespace_stripped() -> None:
    """The effective GHL id is stripped before the URL is built."""
    inputs = _empty_inputs()
    inputs["custom_ghl_id"] = "  cal-pad  "
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.custom_ghl_id == "cal-pad"
    assert result.ghl_calendar_id == f"{GHL_PREFIX}/cal-pad"


# --- TrackStat / Sked formatters (monolith parity) -------------------------------


def test_format_trackstat_url_passthrough() -> None:
    already = f"{TRACKSTAT_PREFIX}/embedded/book?clinic=42"
    assert format_trackstat_url(already) == already


def test_format_trackstat_url_canonical() -> None:
    assert format_trackstat_url("42") == f"{TRACKSTAT_PREFIX}/embedded/book?clinic=42"


def test_format_trackstat_url_query_append() -> None:
    assert format_trackstat_url("a?b=c") == f"{TRACKSTAT_PREFIX}&clinic=a?b=c"


def test_format_sked_url_passthrough() -> None:
    already = f"{SKED_PREFIX}?key=k1"
    assert format_sked_url(already) == already


def test_format_sked_url_canonical() -> None:
    assert format_sked_url("k1") == f"{SKED_PREFIX}?key=k1"


def test_format_sked_url_query_append() -> None:
    assert format_sked_url("a?x=y") == f"{SKED_PREFIX}&key=a?x=y"


def test_build_ghl_url_singular_and_plural() -> None:
    assert build_ghl_url("c1") == f"{GHL_PREFIX}/c1"
    assert build_ghl_url("c1", prefer_plural=True) == f"{GHL_PREFIX_ALT}/c1"


# --- derive_effective_ghl_id (empty-fallback precedence) -------------------------


def test_derive_effective_ghl_explicit_wins() -> None:
    assert derive_effective_ghl_id("explicit", "fallback") == "explicit"


def test_derive_effective_ghl_falls_back_when_explicit_empty() -> None:
    assert derive_effective_ghl_id("", "fallback") == "fallback"
    assert derive_effective_ghl_id(None, "fallback") == "fallback"
    assert derive_effective_ghl_id("   ", "fallback") == "fallback"


def test_derive_effective_ghl_both_empty_is_none() -> None:
    assert derive_effective_ghl_id(None, None) is None
    assert derive_effective_ghl_id("", "  ") is None


def test_derive_effective_ghl_no_fallback_arg() -> None:
    assert derive_effective_ghl_id("explicit") == "explicit"
    assert derive_effective_ghl_id(None) is None


# --- contract drift guards -------------------------------------------------------


def test_source_to_stratum_covers_full_cascade() -> None:
    """Every cascade source field has a stratum mapping (no silent gap)."""
    assert set(SOURCE_TO_STRATUM) == set(CASCADE_PRIORITY)


def test_stratum_vocabulary_matches_phase1_enum() -> None:
    """The resolver's stratum vocabulary is a subset of the Phase-1 enum."""
    produced = set(SOURCE_TO_STRATUM.values()) | {INACTIVE_STRATUM}
    assert produced <= _PHASE1_STRATUM_ENUM
    # And the resolver can produce every non-inactive enum member except those the
    # Phase-1 enum carries for the read-route fallback only (none here).
    assert produced == _PHASE1_STRATUM_ENUM
