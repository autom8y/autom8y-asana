"""Discriminating two-sided fixtures for the RUL-22 ninth source field (gcal-S2).

Locks the WS-PRODUCER half of ADR-gcal-intent-surface-contract §2.2 / §7 (S2):
the INTENT-sourced ``served_calendar_id`` calendar identity, the
``NO_CANONICAL_URL_FIELDS`` embed guard, and C-4 (no ``Business()`` on the read
path). Every fixture is TWO-SIDED (``discriminating-canary-doctrine``): a GREEN arm
that must hold with the cure present, paired with a RED arm that must fail if the
cure is absent or wrong, so a no-op implementation cannot pass.

FORK-CASCADE-POS (ARCHITECT AMENDMENT-001 §A-1 / RUL-6): the gcal-vs-ghl cascade
precedence is an OPEN operator ruling, NOT frozen. Where a fixture would otherwise
encode "gcal beats ghl" it DERIVES the expected winner from ``CASCADE_PRIORITY``
order, so an operator relocating the single list index updates the expectation
without a test edit. Position-STABLE facts (gcal reachable when it is the sole
signal; every explicit external provider outranks the intent field under BOTH the
index-7 and terminal-append options) are asserted literally.
"""

from __future__ import annotations

import inspect
import re

import pytest

from autom8_asana.normalizer import scheduling_extractor, scheduling_stratum
from autom8_asana.normalizer.scheduling_stratum import (
    CASCADE_PRIORITY,
    GHL_PREFIX,
    INACTIVE_STRATUM,
    NO_CANONICAL_URL_FIELDS,
    SOURCE_TO_STRATUM,
    build_ghl_url,
    resolve_stratum,
)
from autom8_asana.services import scheduling_stratum_push

pytestmark = [pytest.mark.xdist_group("scheduling_normalizer")]

_GCAL_ID = "c_3f7a9@group.calendar.google.com"


def _empty_inputs() -> dict[str, str | None]:
    return {field: None for field in CASCADE_PRIORITY}


def _earlier_in_cascade(a: str, b: str) -> str:
    """The first-non-empty-wins winner when BOTH ``a`` and ``b`` are populated.

    Derived from the live ``CASCADE_PRIORITY`` order so a FORK-CASCADE-POS operator
    move (RUL-6) is reflected automatically -- the test never hard-codes the walled
    gcal-vs-ghl precedence.
    """
    return a if CASCADE_PRIORITY.index(a) < CASCADE_PRIORITY.index(b) else b


# --- F-1: gcal reachable + no fabrication ---------------------------------------


def test_f1_green_only_google_cal_id_resolves_gcal_with_identity() -> None:
    """Only ``google_cal_id`` populated -> stratum gcal + served_calendar_id == the id.

    Position-independent: with every other field empty, ``google_cal_id`` is the sole
    non-empty signal and wins at ANY cascade index.
    """
    inputs = _empty_inputs()
    inputs["google_cal_id"] = _GCAL_ID
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.stratum == "gcal"
    assert result.served_calendar_id == _GCAL_ID


def test_f1_red_no_intent_field_never_fabricates_identity() -> None:
    """No ``google_cal_id`` -> served_calendar_id is None and stratum is never gcal.

    RED arm: an implementation that fabricated an identity (or defaulted the plane to
    gcal) would fail here.
    """
    result = resolve_stratum(_empty_inputs(), CASCADE_PRIORITY)
    assert result.served_calendar_id is None
    assert result.stratum != "gcal"
    assert result.stratum == INACTIVE_STRATUM


def test_f1_red_non_gcal_winner_carries_no_served_identity() -> None:
    """A non-gcal, non-ghl winner (calendly) -> served_calendar_id is None.

    Those planes' identity is a destination URL on canonical_destination_url; they
    have no calendar-id-grain identifier, so no served identity may be fabricated.
    """
    inputs = _empty_inputs()
    inputs["calendly_url"] = "https://calendly.com/office-a"
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.stratum == "calendly"
    assert result.served_calendar_id is None


def test_f1_served_calendar_id_is_stripped() -> None:
    """Surrounding whitespace is stripped before the identity is carried."""
    inputs = _empty_inputs()
    inputs["google_cal_id"] = f"  {_GCAL_ID}  "
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.served_calendar_id == _GCAL_ID


# --- F-2: cascade interaction with ghl (position derived) + external precedence ---


def test_f2_green_both_populated_resolves_by_cascade_and_keeps_ghl_fallback() -> None:
    """google_cal_id + custom_ghl_id both populated: deterministic + GHL coords carried.

    The winning plane is DERIVED from CASCADE_PRIORITY (FORK-CASCADE-POS: at the
    interim index-7 recommendation this is gcal; an operator move re-derives it). The
    LOAD-BEARING, position-independent guarantee is that the GHL fail-closed
    coordinates are STILL carried on every result so the data side's beyond-TTL
    fallback works even for a gcal winner.
    """
    inputs = _empty_inputs()
    inputs["google_cal_id"] = _GCAL_ID
    inputs["custom_ghl_id"] = "cal-ghl"
    result = resolve_stratum(inputs, CASCADE_PRIORITY)

    winner = _earlier_in_cascade("google_cal_id", "custom_ghl_id")
    assert result.stratum == SOURCE_TO_STRATUM[winner]
    # Always-carried fail-closed GHL coordinates (independent of the winning plane).
    assert result.custom_ghl_id == "cal-ghl"
    assert result.ghl_calendar_id == build_ghl_url("cal-ghl")


def test_f2_red_explicit_external_provider_still_wins_over_intent_field() -> None:
    """calendly + google_cal_id -> calendly wins (explicit external outranks intent).

    Position-STABLE: ``google_cal_id`` sits after every explicit external provider
    under BOTH live FORK-CASCADE-POS options (index-7 and terminal-append), so this
    is asserted literally -- it is NOT the walled gcal-vs-ghl precedence.
    """
    inputs = _empty_inputs()
    inputs["calendly_url"] = "https://calendly.com/office-a"
    inputs["google_cal_id"] = _GCAL_ID
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.stratum == "calendly"
    assert result.served_calendar_id is None


# --- F-3: canonical_destination_url guard (NO_CANONICAL_URL_FIELDS) ---------------


def test_f3_green_gcal_winner_yields_no_canonical_url() -> None:
    """A google_cal_id winner -> canonical_destination_url is None (embed guard)."""
    assert "google_cal_id" in NO_CANONICAL_URL_FIELDS
    inputs = _empty_inputs()
    inputs["google_cal_id"] = _GCAL_ID
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.canonical_destination_url is None


def test_f3_red_gcal_id_never_raw_forwarded_as_booking_url() -> None:
    """RED arm: the bare calendar id must NOT leak into canonical_destination_url.

    This is exactly the R3 defect the ``NO_CANONICAL_URL_FIELDS`` guard prevents --
    today's ``return winning_value`` fall-through would publish the id as a booking URL.
    """
    inputs = _empty_inputs()
    inputs["google_cal_id"] = _GCAL_ID
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.canonical_destination_url != _GCAL_ID


# --- F-4: ghl winner served_calendar_id is the RAW id, not the widget URL ---------


def test_f4_green_ghl_winner_serves_raw_effective_id() -> None:
    """A custom_ghl_id winner -> served_calendar_id == the RAW effective id."""
    inputs = _empty_inputs()
    inputs["custom_ghl_id"] = "cal-ghl-raw"
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.stratum == "ghl"
    assert result.served_calendar_id == "cal-ghl-raw"


def test_f4_red_ghl_served_identity_is_not_the_widget_url() -> None:
    """RED arm: served_calendar_id must NOT be build_ghl_url(id).

    leg2/leg3 join at raw calendar-id grain; a widget URL here fails the downstream
    exact-string JOIN by construction. ghl_calendar_id carries the URL; the served
    identity carries the raw id -- and they must differ.
    """
    inputs = _empty_inputs()
    inputs["custom_ghl_id"] = "cal-ghl-raw"
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.served_calendar_id != build_ghl_url("cal-ghl-raw")
    assert result.ghl_calendar_id == f"{GHL_PREFIX}/cal-ghl-raw"
    assert result.served_calendar_id != result.ghl_calendar_id


# --- C-4: no Business() instantiation on the producer read path ------------------


@pytest.mark.parametrize(
    "module",
    [scheduling_stratum, scheduling_extractor, scheduling_stratum_push],
    ids=["scheduling_stratum", "scheduling_extractor", "scheduling_stratum_push"],
)
def test_c4_producer_chain_never_instantiates_business(module: object) -> None:
    """C-4: the intent-read producer chain never instantiates a monolith Business().

    ``Business()`` init WRITES (a standing scar); the producer reads Asana through
    warmed frames / raw REST only. A structural source scan keeps the read path free
    of any ``Business(`` call.
    """
    source = inspect.getsource(module)
    assert re.search(r"\bBusiness\s*\(", source) is None, (
        f"{module.__name__} must not instantiate Business() on the read path (C-4)"
    )
