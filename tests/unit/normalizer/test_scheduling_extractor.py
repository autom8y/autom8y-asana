"""Tests for the scheduling-source extractor (the I/O boundary).

Covers: the PURE ``map_resolved_to_inputs`` projection (the eight fields by name +
guid + duration fold), a REAL GFR dynvocab by-name robustness pass (the eight
logical names match differently-cased/spaced Asana display names), and the async
``extract_scheduling_inputs`` happy / defensive-reresolve / guid-absent paths.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.normalizer.scheduling_extractor import (
    GUID_FIELD,
    extract_scheduling_inputs,
    map_resolved_to_inputs,
)
from autom8_asana.normalizer.scheduling_stratum import CASCADE_PRIORITY
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
