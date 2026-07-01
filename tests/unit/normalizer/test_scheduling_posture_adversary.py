"""Adversarial QA fixtures for the scheduling-posture PRODUCER (extraction + winner-URL).

Done-bar: correctness of the EXTRACTED BUSINESS TRUTHS, not legacy parity. Each
test here is authored to fire RED on a deliberately-broken producer variant and
GREEN on the correct build (two-sided). Covers:

  * (f) EXTRACTION EDGES -- INACTIVE -> enrolled=False; absent/unset -> ACTIVE
    default -> enrolled=True; the de-enrolled office keeps its resolved provider
    category (enrollment is ORTHOGONAL to the cascade).
  * (g) WINNER-URL -- DIRECT categories forward the raw external destination; the
    trackstat/sked formatters produce their URL; nothing-resolves -> null (NEVER a
    fabricated URL, and never a ``.../<empty>`` GHL URL); ghl_ownership trichotomy
    edges incl. the explicit+duration -> client_owned precedence.
"""

from __future__ import annotations

import pytest

from autom8_asana.normalizer.scheduling_extractor import (
    CUSTOM_CAL_STATUS_FIELD,
    GUID_FIELD,
    derive_enrolled,
    map_resolved_to_inputs,
)
from autom8_asana.normalizer.scheduling_stratum import (
    CASCADE_PRIORITY,
    GHL_OWNERSHIP_CLIENT_OWNED,
    GHL_OWNERSHIP_INTERNAL_DURATION,
    GHL_OWNERSHIP_NONE,
    INACTIVE_STRATUM,
    derive_ghl_ownership,
    resolve_stratum,
)
from autom8_asana.resolution.gfr.models import (
    FieldStatus,
    FieldWithProvenance,
    ResolvedFields,
    TruthTier,
)

pytestmark = [pytest.mark.xdist_group("scheduling_normalizer")]


def _empty() -> dict[str, str | None]:
    return {f: None for f in CASCADE_PRIORITY}


def _fwp(value: object) -> FieldWithProvenance:
    return FieldWithProvenance(value=value, status=FieldStatus.FRESH, source=TruthTier.CACHE)


def _resolved(gid: str, values: dict[str, object]) -> ResolvedFields:
    return ResolvedFields(gid=gid, rows=[{k: _fwp(v) for k, v in values.items()}], row_count=1)


# --- (f) EXTRACTION EDGES -------------------------------------------------------


def test_f_inactive_projects_enrolled_false() -> None:
    """INACTIVE status -> enrolled=False (the de-enrollment business truth)."""
    assert derive_enrolled("Inactive") is False
    values = {GUID_FIELD: "g", **_empty(), CUSTOM_CAL_STATUS_FIELD: "Inactive"}
    extracted = map_resolved_to_inputs(_resolved("O", values))
    assert extracted.enrolled is False


def test_f_absent_status_degrades_to_active_default_enrolled_true() -> None:
    """Absent/unset/present-but-null status -> legacy ACTIVE default -> enrolled=True.

    Fail-safe DIRECTION: a drifted office whose status field is genuinely absent
    (governed-strict drop) must NOT be silently de-enrolled -- it defaults enrolled.
    """
    assert derive_enrolled(None) is True
    assert derive_enrolled("") is True
    assert derive_enrolled("   ") is True
    # No status key in the row at all -> ACTIVE default.
    extracted = map_resolved_to_inputs(_resolved("O", {GUID_FIELD: "g", **_empty()}))
    assert extracted.enrolled is True


def test_f_deenrolled_office_keeps_resolved_category() -> None:
    """A de-enrolled INACTIVE office STILL resolves its provider (orthogonality).

    Enrollment must not blank the cascade: an INACTIVE office with a live provider
    keeps its stratum + canonical URL (the data side decides serve/withhold, not the
    producer).
    """
    values = {
        GUID_FIELD: "g",
        **_empty(),
        CUSTOM_CAL_STATUS_FIELD: "Inactive",
        "calendly_url": "https://calendly.com/x",
    }
    extracted = map_resolved_to_inputs(_resolved("O", values))
    result = resolve_stratum(
        extracted.normalized_inputs,
        CASCADE_PRIORITY,
        enrolled=extracted.enrolled,
        ghl_ownership=extracted.ghl_ownership,
    )
    assert result.enrolled is False
    assert result.stratum == "calendly"
    assert result.canonical_destination_url == "https://calendly.com/x"


# --- (g) WINNER-URL: no-fabrication + formatter categories ----------------------


def test_g_nothing_resolves_yields_null_never_fabricated() -> None:
    """All-empty cascade -> inactive stratum with NULL urls -- never a fabricated URL."""
    result = resolve_stratum(_empty(), CASCADE_PRIORITY)
    assert result.stratum == INACTIVE_STRATUM
    assert result.canonical_destination_url is None
    assert result.ghl_calendar_id is None
    assert result.custom_ghl_id is None


def test_g_whitespace_only_ghl_id_never_fabricates_empty_url() -> None:
    """A whitespace-only custom_ghl_id must NOT fabricate a ``.../<empty>`` GHL URL."""
    inputs = _empty()
    inputs["custom_ghl_id"] = "   "
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.stratum == INACTIVE_STRATUM
    assert result.canonical_destination_url is None
    assert result.ghl_calendar_id is None


def test_g_direct_category_forwards_raw_external_destination() -> None:
    """A DIRECT provider (janeapp) forwards its raw external URL, un-reformatted."""
    inputs = _empty()
    inputs["janeapp_url"] = "https://office.janeapp.com/book"
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.stratum == "janeapp"
    assert result.canonical_destination_url == "https://office.janeapp.com/book"


def test_g_trackstat_formatter_category_builds_url() -> None:
    inputs = _empty()
    inputs["trackstat_id"] = "clinic-42"
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.stratum == "trackstat"
    assert result.canonical_destination_url == (
        "https://clinic.patienthealthcenters.org/embedded/book?clinic=clinic-42"
    )


def test_g_sked_formatter_category_builds_url() -> None:
    inputs = _empty()
    inputs["sked_id"] = "k1"
    result = resolve_stratum(inputs, CASCADE_PRIORITY)
    assert result.stratum == "sked"
    assert result.canonical_destination_url == "https://portal.sked.life/new-patient?key=k1"


# --- (g) ghl_ownership trichotomy edges -----------------------------------------


def test_g_ownership_explicit_and_duration_both_present_is_client_owned() -> None:
    """PRECEDENCE: an explicit custom_ghl_id wins over a duration fallback -> client_owned."""
    assert derive_ghl_ownership("cal-explicit", "cal-duration") == GHL_OWNERSHIP_CLIENT_OWNED
    # And the extractor derives the SAME precedence pre-fold.
    values = {GUID_FIELD: "g", **_empty(), "custom_ghl_id": "cal-explicit"}
    extracted = map_resolved_to_inputs(_resolved("O", values), duration_fallback_id="cal-duration")
    assert extracted.ghl_ownership == GHL_OWNERSHIP_CLIENT_OWNED
    assert extracted.normalized_inputs["custom_ghl_id"] == "cal-explicit"


def test_g_ownership_duration_only_is_internal_duration() -> None:
    assert derive_ghl_ownership(None, "cal-duration") == GHL_OWNERSHIP_INTERNAL_DURATION
    assert derive_ghl_ownership("  ", "cal-duration") == GHL_OWNERSHIP_INTERNAL_DURATION


def test_g_ownership_neither_is_none() -> None:
    assert derive_ghl_ownership(None, None) == GHL_OWNERSHIP_NONE
    assert derive_ghl_ownership("", "   ") == GHL_OWNERSHIP_NONE
