"""Tests for the scheduling-source extractor (the I/O boundary).

Covers: the PURE ``map_resolved_to_inputs`` projection (the eight fields by name +
guid + duration fold + the wire-contract-v2 enrolled / ghl_ownership axes), the
``derive_enrolled`` INACTIVE/absent semantics, a REAL GFR dynvocab by-name
robustness pass (the eight logical names match differently-cased/spaced Asana
display names), and the async ``extract_scheduling_inputs`` happy /
defensive-reresolve / guid-absent paths.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.normalizer.scheduling_extractor import (
    CUSTOM_CAL_STATUS_FIELD,
    GUID_FIELD,
    derive_enrolled,
    extract_scheduling_inputs,
    map_resolved_to_inputs,
)
from autom8_asana.normalizer.scheduling_stratum import (
    CASCADE_PRIORITY,
    GHL_OWNERSHIP_CLIENT_OWNED,
    GHL_OWNERSHIP_INTERNAL_DURATION,
    GHL_OWNERSHIP_NONE,
)
from autom8_asana.resolution.gfr.dynvocab import resolve_dynamic_fields
from autom8_asana.resolution.gfr.entry import EntryAnchor
from autom8_asana.resolution.gfr.errors import UnresolvedError
from autom8_asana.resolution.gfr.models import (
    FieldStatus,
    FieldWithProvenance,
    ResolvedFields,
    TruthTier,
)
from tests.unit.resolution.gfr.conftest import make_entry_task

pytestmark = [pytest.mark.xdist_group("scheduling_normalizer")]

_EXTRACTOR_MOD = "autom8_asana.normalizer.scheduling_extractor"


def _fwp(value: object) -> FieldWithProvenance:
    return FieldWithProvenance(value=value, status=FieldStatus.FRESH, source=TruthTier.CACHE)


def _resolved(gid: str, values: dict[str, object]) -> ResolvedFields:
    """A single-row ResolvedFields keyed by field name (what GFR by-name returns)."""
    return ResolvedFields(gid=gid, rows=[{k: _fwp(v) for k, v in values.items()}], row_count=1)


# --- derive_enrolled (R-NEW-1 enrollment axis) ----------------------------------


@pytest.mark.parametrize(
    "status", ["Inactive", "INACTIVE", "inactive", " Inactive ", "paused", "off"]
)
def test_derive_enrolled_false_for_inactive_aliases(status: str) -> None:
    """Any INACTIVE alias (monolith BinaryStatus set) gates the office off."""
    assert derive_enrolled(status) is False


@pytest.mark.parametrize("status", ["Active", "ACTIVE", "active", "enabled", "on"])
def test_derive_enrolled_true_for_active_aliases(status: str) -> None:
    assert derive_enrolled(status) is True


def test_derive_enrolled_true_when_absent_or_unset() -> None:
    """Absent / unset / present-but-null -> legacy ACTIVE default -> enrolled."""
    assert derive_enrolled(None) is True
    assert derive_enrolled("") is True
    assert derive_enrolled("   ") is True


def test_derive_enrolled_true_for_unknown_option() -> None:
    """An unrecognized option is NOT an INACTIVE alias -> stays enrolled (ACTIVE)."""
    assert derive_enrolled("SomethingElse") is True


# --- map_resolved_to_inputs: enrolled + ghl_ownership (wire contract v2) ---------


def _base_values(gid: str = "guid-1") -> dict[str, object]:
    return {GUID_FIELD: gid, **{f: None for f in CASCADE_PRIORITY}}


def test_map_projects_enrolled_from_inactive_status() -> None:
    """An INACTIVE office is de-enrolled but STILL produced (present, enrolled=False)."""
    values = {**_base_values(), CUSTOM_CAL_STATUS_FIELD: "Inactive", "reviewwave_id": "rw"}
    extracted = map_resolved_to_inputs(_resolved("O1", values))
    assert extracted.enrolled is False
    # De-enrolled offices keep their resolved inputs (enrollment is orthogonal).
    assert extracted.normalized_inputs["reviewwave_id"] == "rw"


def test_map_projects_enrolled_true_when_status_absent() -> None:
    """No status field in the row -> legacy ACTIVE default -> enrolled."""
    extracted = map_resolved_to_inputs(_resolved("O1", _base_values()))
    assert extracted.enrolled is True


def test_map_ghl_ownership_client_owned_from_explicit() -> None:
    """An explicit custom_ghl_id -> client_owned (and folds to the effective id)."""
    values = {**_base_values(), "custom_ghl_id": "cal-explicit"}
    extracted = map_resolved_to_inputs(_resolved("O1", values), duration_fallback_id="cal-dur")
    assert extracted.ghl_ownership == GHL_OWNERSHIP_CLIENT_OWNED
    assert extracted.normalized_inputs["custom_ghl_id"] == "cal-explicit"


def test_map_ghl_ownership_internal_duration_from_fallback() -> None:
    """No explicit id but a duration fallback -> internal_duration (folded id = fallback).

    Proves ownership is derived from the PRE-fold provenance -- after the fold the
    custom_ghl_id slot holds the duration id, but ownership already recorded the slot.
    """
    values = {**_base_values(), "custom_ghl_id": None}
    extracted = map_resolved_to_inputs(_resolved("O1", values), duration_fallback_id="cal-dur")
    assert extracted.ghl_ownership == GHL_OWNERSHIP_INTERNAL_DURATION
    assert extracted.normalized_inputs["custom_ghl_id"] == "cal-dur"


def test_map_ghl_ownership_none_when_neither() -> None:
    extracted = map_resolved_to_inputs(_resolved("O1", _base_values()))
    assert extracted.ghl_ownership == GHL_OWNERSHIP_NONE
    assert extracted.normalized_inputs["custom_ghl_id"] is None


# --- PURE mapping ---------------------------------------------------------------


def test_map_resolved_maps_eight_by_name() -> None:
    values: dict[str, object] = {GUID_FIELD: "guid-1"}
    for field in CASCADE_PRIORITY:
        values[field] = f"v-{field}"
    extracted = map_resolved_to_inputs(_resolved("O1", values))

    assert extracted.guid == "guid-1"
    for field in CASCADE_PRIORITY:
        assert extracted.normalized_inputs[field] == f"v-{field}"


def test_map_resolved_present_but_null_is_none() -> None:
    values = {GUID_FIELD: "guid-1", **{f: None for f in CASCADE_PRIORITY}}
    values["reviewwave_id"] = "rw"
    extracted = map_resolved_to_inputs(_resolved("O1", values))
    assert extracted.normalized_inputs["reviewwave_id"] == "rw"
    assert extracted.normalized_inputs["acuity_cal_url"] is None


def test_map_resolved_missing_field_is_none() -> None:
    """A field absent from the resolved row maps to None (defensive)."""
    extracted = map_resolved_to_inputs(_resolved("O1", {GUID_FIELD: "guid-1"}))
    for field in CASCADE_PRIORITY:
        assert extracted.normalized_inputs[field] is None


def test_map_resolved_folds_duration_fallback() -> None:
    values = {GUID_FIELD: "guid-1", **{f: None for f in CASCADE_PRIORITY}}
    extracted = map_resolved_to_inputs(_resolved("O1", values), duration_fallback_id="cal-dur")
    assert extracted.normalized_inputs["custom_ghl_id"] == "cal-dur"


def test_map_resolved_explicit_ghl_wins_over_fallback() -> None:
    values = {GUID_FIELD: "guid-1", **{f: None for f in CASCADE_PRIORITY}}
    values["custom_ghl_id"] = "explicit"
    extracted = map_resolved_to_inputs(_resolved("O1", values), duration_fallback_id="cal-dur")
    assert extracted.normalized_inputs["custom_ghl_id"] == "explicit"


def test_map_resolved_no_guid_raises() -> None:
    with pytest.raises(ValueError, match=GUID_FIELD):
        map_resolved_to_inputs(_resolved("O1", {GUID_FIELD: None}))


# --- REAL dynvocab by-name robustness (NameNormalizer case/space/underscore) -----


def test_eight_logical_names_match_varied_asana_display_names() -> None:
    """The eight logical names resolve against differently-cased Asana cf names.

    Proves the by-name path is NameNormalizer-robust end-to-end (not just trusting a
    mock): the Asana display names below differ in case/spacing/underscore from the
    CASCADE_PRIORITY logical names, yet all eight resolve.
    """
    custom_fields: list[dict[str, Any]] = [
        {"gid": "1", "name": "ReviewWave ID", "resource_subtype": "text", "text_value": "rw-9"},
        {"gid": "2", "name": "Acuity Cal URL", "resource_subtype": "text", "text_value": "ac-9"},
        {"gid": "3", "name": "Calendly Url", "resource_subtype": "text", "text_value": "ca-9"},
        {"gid": "4", "name": "JaneApp URL", "resource_subtype": "text", "text_value": "ja-9"},
        {"gid": "5", "name": "EHR Cal URL", "resource_subtype": "text", "text_value": "eh-9"},
        {"gid": "6", "name": "TrackStat ID", "resource_subtype": "text", "text_value": "tr-9"},
        {"gid": "7", "name": "Sked ID", "resource_subtype": "text", "text_value": "sk-9"},
        {"gid": "8", "name": "Custom GHL ID", "resource_subtype": "text", "text_value": "gh-9"},
    ]
    anchor = EntryAnchor(
        gid="O9",
        entity_type=EntityType.OFFER,
        business_gid="B9",
        path_len=3,
        entry_task=make_entry_task(gid="O9", custom_fields=custom_fields),
    )
    resolved = resolve_dynamic_fields(anchor=anchor, fields=list(CASCADE_PRIORITY))
    row = resolved.scalar()
    assert {f: row[f].value for f in CASCADE_PRIORITY} == {
        "reviewwave_id": "rw-9",
        "acuity_cal_url": "ac-9",
        "calendly_url": "ca-9",
        "janeapp_url": "ja-9",
        "ehr_cal_url": "eh-9",
        "trackstat_id": "tr-9",
        "sked_id": "sk-9",
        "custom_ghl_id": "gh-9",
    }


# --- async extract_scheduling_inputs --------------------------------------------


async def test_extract_async_happy_path() -> None:
    values = {GUID_FIELD: "guid-1", **{f: f"v-{f}" for f in CASCADE_PRIORITY}}
    with patch(
        f"{_EXTRACTOR_MOD}.resolve_async", new=AsyncMock(return_value=_resolved("O1", values))
    ):
        extracted = await extract_scheduling_inputs("O1", client=object(), query_engine=object())
    assert extracted.guid == "guid-1"
    assert extracted.normalized_inputs["sked_id"] == "v-sked_id"


async def test_extract_async_defensive_reresolve_on_unknown_field() -> None:
    """A genuinely-absent source field re-resolves the present subset (absent->None)."""
    present_values = {GUID_FIELD: "guid-1", "reviewwave_id": "rw"}
    mock = AsyncMock(
        side_effect=[
            UnresolvedError(fields=["trackstat_id", "sked_id"], reason="unknown-field"),
            _resolved("O1", present_values),
        ]
    )
    with patch(f"{_EXTRACTOR_MOD}.resolve_async", new=mock):
        extracted = await extract_scheduling_inputs("O1", client=object(), query_engine=object())

    assert mock.await_count == 2
    # Second call requested the present subset only (absent fields dropped).
    second_fields = mock.await_args_list[1].args[1]
    assert "trackstat_id" not in second_fields
    assert "sked_id" not in second_fields
    assert extracted.guid == "guid-1"
    assert extracted.normalized_inputs["reviewwave_id"] == "rw"
    assert extracted.normalized_inputs["trackstat_id"] is None


async def test_extract_async_reraises_when_guid_absent() -> None:
    """If company_id itself is unresolvable, the office has no usable guid -> raise."""
    mock = AsyncMock(side_effect=UnresolvedError(fields=[GUID_FIELD], reason="unknown-field"))
    with patch(f"{_EXTRACTOR_MOD}.resolve_async", new=mock), pytest.raises(UnresolvedError):
        await extract_scheduling_inputs("O1", client=object(), query_engine=object())
    assert mock.await_count == 1


async def test_extract_async_requests_custom_cal_status() -> None:
    """The entry resolve requests the enrollment-status field alongside the eight."""
    values = {GUID_FIELD: "guid-1", CUSTOM_CAL_STATUS_FIELD: "Active"}
    mock = AsyncMock(return_value=_resolved("O1", values))
    with patch(f"{_EXTRACTOR_MOD}.resolve_async", new=mock):
        extracted = await extract_scheduling_inputs("O1", client=object(), query_engine=object())
    requested = mock.await_args.args[1]
    assert CUSTOM_CAL_STATUS_FIELD in requested
    assert extracted.enrolled is True


async def test_extract_async_status_absent_degrades_to_enrolled() -> None:
    """A missing status field (governed-strict drop) fails safe to the ACTIVE default."""
    mock = AsyncMock(
        side_effect=[
            UnresolvedError(fields=[CUSTOM_CAL_STATUS_FIELD], reason="unknown-field"),
            _resolved("O1", {GUID_FIELD: "guid-1", "reviewwave_id": "rw"}),
        ]
    )
    with patch(f"{_EXTRACTOR_MOD}.resolve_async", new=mock):
        extracted = await extract_scheduling_inputs("O1", client=object(), query_engine=object())
    # status absent from the re-resolved row -> enrolled True (legacy ACTIVE default).
    assert extracted.enrolled is True
    assert extracted.normalized_inputs["reviewwave_id"] == "rw"


def test_real_gfr_reads_enum_status_by_name() -> None:
    """A REAL GFR by-name pass types an enum ``custom_cal_status`` -> the option name.

    Proves the enrollment read works end-to-end against an enum cf (not just a mock):
    the ``enum`` resource_subtype surfaces the option NAME the projection feeds to
    ``derive_enrolled``.
    """
    custom_fields: list[dict[str, Any]] = [
        {
            "gid": "s",
            "name": "Custom Cal Status",
            "resource_subtype": "enum",
            "enum_value": {"gid": "e", "name": "Inactive"},
        },
    ]
    anchor = EntryAnchor(
        gid="O9",
        entity_type=EntityType.OFFER,
        business_gid="B9",
        path_len=3,
        entry_task=make_entry_task(gid="O9", custom_fields=custom_fields),
    )
    resolved = resolve_dynamic_fields(anchor=anchor, fields=[CUSTOM_CAL_STATUS_FIELD])
    row = resolved.scalar()
    assert row[CUSTOM_CAL_STATUS_FIELD].value == "Inactive"
    assert derive_enrolled(row[CUSTOM_CAL_STATUS_FIELD].value) is False
