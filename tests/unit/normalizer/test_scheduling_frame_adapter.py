"""Tests for the PURE frame-first adapter ``map_frame_row_to_inputs`` (FORK-1 A∘D).

The frame-first twin of ``map_resolved_to_inputs``: it projects a WARMED offer-frame
row dict (the 1.5.0 posture columns) onto the cascade inputs + the wire-v2 axes with
ZERO Asana calls. Covers:

  * the frame-hit path (all posture columns present -> correct ExtractedScheduling incl.
    the enrolled derivation);
  * absent/unset custom_cal_status -> legacy ACTIVE default -> enrolled=True (never
    fabricated -- a null column is legitimate absence);
  * de-enrolled (INACTIVE) -> enrolled=False, STILL produced (orthogonal to cascade);
  * the SCHEMA-LAG guard: a row LACKING the projected columns REFUSES (two-sided --
    RED on a fabricating variant, GREEN on the refusing build) -- never default-fills;
  * VECTORIZED-vs-REFERENCE equivalence: the frame adapter is byte-equivalent to the
    GFR-path ``map_resolved_to_inputs`` for the same office data.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest

from autom8_asana.normalizer.scheduling_extractor import (
    CUSTOM_CAL_STATUS_FIELD,
    GUID_FIELD,
    REQUIRED_FRAME_COLUMNS,
    FrameSchemaLagError,
    map_frame_row_to_inputs,
    map_resolved_to_inputs,
    missing_frame_columns,
)
from autom8_asana.normalizer.scheduling_stratum import (
    CASCADE_PRIORITY,
    GHL_OWNERSHIP_CLIENT_OWNED,
    GHL_OWNERSHIP_NONE,
)
from autom8_asana.resolution.gfr.models import (
    FieldStatus,
    FieldWithProvenance,
    ResolvedFields,
    TruthTier,
)

pytestmark = [pytest.mark.xdist_group("scheduling_normalizer")]


def _frame_row(guid: str | None = "guid-1", **overrides: Any) -> dict[str, Any]:
    """A complete 1.5.0 offer-frame row dict (all posture columns present as keys)."""
    row: dict[str, Any] = {
        "gid": "o-1",
        "last_modified": dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        GUID_FIELD: guid,
        CUSTOM_CAL_STATUS_FIELD: None,
    }
    for field in CASCADE_PRIORITY:
        row[field] = None
    row.update(overrides)
    return row


# --- REQUIRED_FRAME_COLUMNS + missing_frame_columns -----------------------------


def test_required_frame_columns_are_guid_status_and_cascade() -> None:
    expected = (GUID_FIELD, CUSTOM_CAL_STATUS_FIELD, *CASCADE_PRIORITY)
    assert expected == REQUIRED_FRAME_COLUMNS


def test_missing_frame_columns_none_when_all_present() -> None:
    assert missing_frame_columns(["gid", "last_modified", *REQUIRED_FRAME_COLUMNS]) == []


def test_missing_frame_columns_lists_absent_posture_columns() -> None:
    """A pre-1.5.0 frame (only base columns) reports every posture column as missing."""
    missing = missing_frame_columns(["gid", "name", "last_modified"])
    assert set(missing) == set(REQUIRED_FRAME_COLUMNS)
    # Order-preserved (matches REQUIRED_FRAME_COLUMNS order).
    assert missing == list(REQUIRED_FRAME_COLUMNS)


# --- frame-hit path + enrolled derivation ---------------------------------------


def test_frame_hit_maps_cascade_and_guid() -> None:
    row = _frame_row(guid="g-hit", reviewwave_id="rw", calendly_url="cal")
    extracted = map_frame_row_to_inputs(row)
    assert extracted.guid == "g-hit"
    assert extracted.normalized_inputs["reviewwave_id"] == "rw"
    assert extracted.normalized_inputs["calendly_url"] == "cal"


def test_frame_hit_absent_status_defaults_active_enrolled() -> None:
    """A null custom_cal_status column -> legacy ACTIVE default -> enrolled=True."""
    extracted = map_frame_row_to_inputs(_frame_row())
    assert extracted.enrolled is True


def test_frame_hit_inactive_status_is_deenrolled_but_present() -> None:
    """INACTIVE -> enrolled=False, and the office is STILL produced (orthogonal)."""
    row = _frame_row(guid="g-off", **{CUSTOM_CAL_STATUS_FIELD: "Inactive"}, sked_id="sk")
    extracted = map_frame_row_to_inputs(row)
    assert extracted.enrolled is False
    assert extracted.normalized_inputs["sked_id"] == "sk"  # category preserved


def test_frame_ghl_ownership_client_owned_from_explicit() -> None:
    row = _frame_row(custom_ghl_id="cal-explicit")
    extracted = map_frame_row_to_inputs(row)
    assert extracted.ghl_ownership == GHL_OWNERSHIP_CLIENT_OWNED
    assert extracted.normalized_inputs["custom_ghl_id"] == "cal-explicit"


def test_frame_ghl_ownership_none_when_no_slot() -> None:
    extracted = map_frame_row_to_inputs(_frame_row())
    assert extracted.ghl_ownership == GHL_OWNERSHIP_NONE
    assert extracted.normalized_inputs["custom_ghl_id"] is None


def test_frame_no_guid_raises() -> None:
    with pytest.raises(ValueError, match=GUID_FIELD):
        map_frame_row_to_inputs(_frame_row(guid=None))


# --- SCHEMA-LAG guard (two-sided: fabricating RED / refusing GREEN) -------------


def test_frame_schema_lag_row_refuses() -> None:
    """A row LACKING the projected posture columns (pre-1.5.0) REFUSES honestly."""
    stale_row = {"gid": "o1", GUID_FIELD: "g1"}  # no custom_cal_status / cascade keys
    with pytest.raises(FrameSchemaLagError, match="pre-1.5.0"):
        map_frame_row_to_inputs(stale_row)


def test_frame_schema_lag_fabricating_variant_is_the_danger() -> None:
    """RED-on-fabricating: a variant that ``.get(col, None)`` invents an ACTIVE posture.

    This documents the exact hazard the SCHEMA-LAG guard exists to stop: a pre-1.5.0
    row silently defaults the absent status to the ACTIVE default (enrolled=True),
    fabricating posture from a frame that cannot carry it. The refusing build
    (test above) raises instead.
    """
    from autom8_asana.normalizer.scheduling_extractor import derive_enrolled

    stale_row: dict[str, Any] = {"gid": "o1", GUID_FIELD: "g1"}
    # The fabricating variant does NOT raise -- it invents enrolled=True.
    fabricated = derive_enrolled(stale_row.get(CUSTOM_CAL_STATUS_FIELD))
    assert fabricated is True


# --- VECTORIZED-vs-REFERENCE equivalence (frame adapter == GFR-path adapter) -----


def _resolved(guid: str, values: dict[str, object]) -> ResolvedFields:
    def fwp(v: object) -> FieldWithProvenance:
        return FieldWithProvenance(value=v, status=FieldStatus.FRESH, source=TruthTier.CACHE)

    return ResolvedFields(gid=guid, rows=[{k: fwp(v) for k, v in values.items()}], row_count=1)


@pytest.mark.parametrize(
    "values",
    [
        {GUID_FIELD: "gEq", CUSTOM_CAL_STATUS_FIELD: "Inactive", "calendly_url": "cal"},
        {GUID_FIELD: "gEq2", "reviewwave_id": "rw", "custom_ghl_id": "gh"},
        {GUID_FIELD: "gEq3", CUSTOM_CAL_STATUS_FIELD: "Active"},
        {GUID_FIELD: "gEq4", "trackstat_id": "ts", "sked_id": "sk"},
    ],
)
def test_frame_adapter_equivalent_to_resolved_adapter(values: dict[str, object]) -> None:
    """The frame-first adapter is byte-equivalent to the GFR-path reference adapter.

    For the same office data, ``map_frame_row_to_inputs`` (frame-first) and
    ``map_resolved_to_inputs`` (GFR-path reference) produce an IDENTICAL
    ExtractedScheduling -- proving the frame-first swap preserves the wire-v2 axes
    {enrolled, canonical_destination_url (downstream), ghl_ownership} + the cascade.
    """
    full = {GUID_FIELD: values[GUID_FIELD], CUSTOM_CAL_STATUS_FIELD: None}
    for field in CASCADE_PRIORITY:
        full[field] = None
    full.update(values)

    reference = map_resolved_to_inputs(_resolved("O-eq", dict(full)))
    frame = map_frame_row_to_inputs(_frame_row(**full))  # type: ignore[arg-type]

    assert frame == reference
