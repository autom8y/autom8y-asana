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
    GHL_OWNERSHIP_CLIENT_OWNED,
    GHL_OWNERSHIP_INTERNAL_DURATION,
    GHL_OWNERSHIP_NONE,
    GHL_OWNERSHIP_VALUES,
    GHL_PREFIX,
    GHL_PREFIX_ALT,
    INACTIVE_STRATUM,
    SKED_PREFIX,
    SOURCE_TO_STRATUM,
    TRACKSTAT_PREFIX,
    StratumResult,
    build_ghl_url,
    derive_effective_ghl_id,
    derive_ghl_ownership,
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
    """custom_ghl_id as the sole signal -> ghl stratum + derived booking URL.

    The GHL winner's canonical destination URL IS the derived booking URL (the
    same value carried on ``ghl_calendar_id``).
    """
    inputs = _empty_inputs()
    inputs["custom_ghl_id"] = "cal-xyz"
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result == StratumResult(
        stratum="ghl",
        custom_ghl_id="cal-xyz",
        ghl_calendar_id=f"{GHL_PREFIX}/cal-xyz",
        canonical_destination_url=f"{GHL_PREFIX}/cal-xyz",
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


# --- wire contract v2: canonical destination URL (R-NEW-2) -----------------------


@pytest.mark.parametrize(
    ("winning_field", "raw_value", "expected_url"),
    [
        # DIRECT / already-a-URL providers forward the raw external destination.
        (
            "reviewwave_id",
            "https://reviewwave.example/book/rw-1",
            "https://reviewwave.example/book/rw-1",
        ),
        (
            "acuity_cal_url",
            "https://app.acuityscheduling.com/x",
            "https://app.acuityscheduling.com/x",
        ),
        ("calendly_url", "https://calendly.com/office-a", "https://calendly.com/office-a"),
        ("janeapp_url", "https://office.janeapp.com/", "https://office.janeapp.com/"),
        ("ehr_cal_url", "https://ehr.example/portal", "https://ehr.example/portal"),
    ],
)
def test_canonical_url_direct_providers_forward_raw(
    winning_field: str, raw_value: str, expected_url: str
) -> None:
    """The URL-bearing / DIRECT providers forward their raw external destination."""
    inputs = _empty_inputs()
    inputs[winning_field] = raw_value
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.canonical_destination_url == expected_url


def test_canonical_url_trackstat_uses_resident_formatter() -> None:
    """A trackstat winner's canonical URL runs through ``format_trackstat_url``."""
    inputs = _empty_inputs()
    inputs["trackstat_id"] = "42"
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.stratum == "trackstat"
    assert result.canonical_destination_url == format_trackstat_url("42")
    assert result.canonical_destination_url == f"{TRACKSTAT_PREFIX}/embedded/book?clinic=42"


def test_canonical_url_sked_uses_resident_formatter() -> None:
    """A sked winner's canonical URL runs through ``format_sked_url``."""
    inputs = _empty_inputs()
    inputs["sked_id"] = "k1"
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.stratum == "sked"
    assert result.canonical_destination_url == format_sked_url("k1")
    assert result.canonical_destination_url == f"{SKED_PREFIX}?key=k1"


def test_canonical_url_ghl_winner_builds_booking_url() -> None:
    """A GHL winner's canonical URL is the derived booking URL."""
    inputs = _empty_inputs()
    inputs["custom_ghl_id"] = "cal-9"
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.stratum == "ghl"
    assert result.canonical_destination_url == build_ghl_url("cal-9")


def test_canonical_url_none_when_inactive() -> None:
    """All-empty -> inactive -> no canonical destination URL resolves."""
    result = resolve_stratum(_empty_inputs(), CASCADE_PRIORITY)
    assert result.stratum == INACTIVE_STRATUM
    assert result.canonical_destination_url is None


def test_canonical_url_winner_is_cascade_winner_not_ghl_fallback() -> None:
    """A non-GHL winner drives the canonical URL; the GHL coord is still carried.

    Proves the canonical URL is the CASCADE winner's destination, distinct from the
    always-carried fail-closed GHL coordinate.
    """
    inputs = _empty_inputs()
    inputs["trackstat_id"] = "77"
    inputs["custom_ghl_id"] = "cal-fallback"
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.stratum == "trackstat"
    assert result.canonical_destination_url == format_trackstat_url("77")
    # GHL fail-closed coordinate is still carried for the read route's fallback.
    assert result.ghl_calendar_id == build_ghl_url("cal-fallback")
    assert result.canonical_destination_url != result.ghl_calendar_id


def test_canonical_url_strips_surrounding_whitespace() -> None:
    """A winning value's surrounding whitespace is stripped before URL construction."""
    inputs = _empty_inputs()
    inputs["acuity_cal_url"] = "  https://app.acuityscheduling.com/pad  "
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.canonical_destination_url == "https://app.acuityscheduling.com/pad"


# --- wire contract v2: ghl_ownership trichotomy (ESC-1 / obligation 4) -----------


def test_ghl_ownership_client_owned_when_explicit_present() -> None:
    assert derive_ghl_ownership("cal-explicit", "cal-duration") == GHL_OWNERSHIP_CLIENT_OWNED
    assert derive_ghl_ownership("cal-explicit", None) == GHL_OWNERSHIP_CLIENT_OWNED


def test_ghl_ownership_internal_duration_when_only_fallback() -> None:
    assert derive_ghl_ownership(None, "cal-duration") == GHL_OWNERSHIP_INTERNAL_DURATION
    assert derive_ghl_ownership("", "cal-duration") == GHL_OWNERSHIP_INTERNAL_DURATION
    assert derive_ghl_ownership("   ", "cal-duration") == GHL_OWNERSHIP_INTERNAL_DURATION


def test_ghl_ownership_none_when_neither() -> None:
    assert derive_ghl_ownership(None, None) == GHL_OWNERSHIP_NONE
    assert derive_ghl_ownership("", "  ") == GHL_OWNERSHIP_NONE


def test_ghl_ownership_mirrors_effective_ghl_precedence() -> None:
    """Ownership trichotomy tracks ``derive_effective_ghl_id``'s winning slot."""
    # explicit wins -> the effective id is the explicit one -> client_owned
    assert derive_effective_ghl_id("exp", "dur") == "exp"
    assert derive_ghl_ownership("exp", "dur") == GHL_OWNERSHIP_CLIENT_OWNED
    # fallback wins -> the effective id is the duration one -> internal_duration
    assert derive_effective_ghl_id(None, "dur") == "dur"
    assert derive_ghl_ownership(None, "dur") == GHL_OWNERSHIP_INTERNAL_DURATION


def test_ghl_ownership_values_is_closed_trichotomy() -> None:
    assert {
        GHL_OWNERSHIP_CLIENT_OWNED,
        GHL_OWNERSHIP_INTERNAL_DURATION,
        GHL_OWNERSHIP_NONE,
    } == GHL_OWNERSHIP_VALUES


# --- wire contract v2: enrolled / ghl_ownership carry-through --------------------


def test_resolver_carries_enrolled_and_ownership_through() -> None:
    """The resolver passes the producer-derived v2 axes onto the result unchanged."""
    inputs = _empty_inputs()
    inputs["calendly_url"] = "https://calendly.com/x"
    result = resolve_stratum(
        inputs,
        CASCADE_PRIORITY,
        enrolled=False,
        ghl_ownership=GHL_OWNERSHIP_CLIENT_OWNED,
    )
    assert result.enrolled is False
    assert result.ghl_ownership == GHL_OWNERSHIP_CLIENT_OWNED
    # Enrollment is ORTHOGONAL to the cascade: a de-enrolled office keeps its
    # resolved provider category and canonical URL.
    assert result.stratum == "calendly"
    assert result.canonical_destination_url == "https://calendly.com/x"


def test_resolver_v2_axes_default_to_legacy_faithful() -> None:
    """A cascade-only caller gets enrolled=True (legacy ACTIVE) + ownership=none."""
    result = resolve_stratum(_empty_inputs(), CASCADE_PRIORITY)
    assert result.enrolled is True
    assert result.ghl_ownership == GHL_OWNERSHIP_NONE


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
