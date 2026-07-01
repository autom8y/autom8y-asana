"""Golden round-trip fixture for the scheduling-posture producer pipeline.

Regenerates two entries through the REAL producer chain (map_resolved_to_inputs ->
resolve_office_entries -> build_stratum_entry) on fixed inputs and asserts they match
the committed ``tests/fixtures/scheduling_posture_golden_entries.json``.  The fixture
is the round-trip station's input to the consumer leg -- this test keeps it a LIVE
artifact (a byte-exact re-derivation), never a stale hand-edit.

The two entries exercise the wire-contract-v2 additions end-to-end:
  * ``office-enrolled-001`` -- enrolled=true, a RESOLVED canonical URL (trackstat
    winner via the resident formatter) + client-owned GHL;
  * ``office-inactive-002`` -- enrolled=false (INACTIVE office) yet STILL PRESENT,
    keeping its resolved provider category (enrollment is orthogonal).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, Field

from autom8_asana.normalizer.scheduling_extractor import (
    CUSTOM_CAL_STATUS_FIELD,
    GUID_FIELD,
    map_resolved_to_inputs,
)
from autom8_asana.normalizer.scheduling_stratum import CASCADE_PRIORITY
from autom8_asana.resolution.gfr.models import (
    FieldStatus,
    FieldWithProvenance,
    ResolvedFields,
    TruthTier,
)
from autom8_asana.services.scheduling_stratum_push import resolve_office_entries

pytestmark = [pytest.mark.xdist_group("scheduling_normalizer")]

_FIXTURE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "scheduling_posture_golden_entries.json"
)

#: Fixed stamp so the round-trip is byte-deterministic.
_STAMP = datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC)


class _WireV2Entry(BaseModel):
    """extra=forbid replica of the frozen wire contract v2 entry surface."""

    model_config = ConfigDict(extra="forbid")
    guid: str = Field(min_length=1, max_length=36)
    stratum: str
    custom_ghl_id: str | None = None
    ghl_calendar_id: str | None = None
    resolved_at: str | None = None
    enrolled: bool
    canonical_destination_url: str | None = None
    ghl_ownership: str


def _fwp(value: object) -> FieldWithProvenance:
    return FieldWithProvenance(value=value, status=FieldStatus.FRESH, source=TruthTier.CACHE)


def _resolved(gid: str, values: dict[str, object]) -> ResolvedFields:
    return ResolvedFields(gid=gid, rows=[{k: _fwp(v) for k, v in values.items()}], row_count=1)


def _generate_golden_entries() -> list[dict[str, object]]:
    """Emit the two golden entries through the real extract -> resolve -> build chain."""
    base = {f: None for f in CASCADE_PRIORITY}
    enrolled_office = _resolved(
        "O1",
        {
            **base,
            GUID_FIELD: "office-enrolled-001",
            CUSTOM_CAL_STATUS_FIELD: "Active",
            "trackstat_id": "clinic-42",
            "custom_ghl_id": "cal-client-1",
        },
    )
    inactive_office = _resolved(
        "O2",
        {
            **base,
            GUID_FIELD: "office-inactive-002",
            CUSTOM_CAL_STATUS_FIELD: "Inactive",
            "calendly_url": "https://calendly.com/office-two",
        },
    )
    extracted = [map_resolved_to_inputs(enrolled_office), map_resolved_to_inputs(inactive_office)]
    return resolve_office_entries(extracted, resolved_at=_STAMP)


def test_golden_fixture_matches_live_pipeline() -> None:
    """The committed fixture is byte-exact to a fresh re-derivation (no drift)."""
    generated = _generate_golden_entries()
    committed = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    # Compare order-independent-per-guid to survive incidental key/order churn.
    by_guid_generated = {e["guid"]: e for e in generated}
    by_guid_committed = {e["guid"]: e for e in committed}
    assert by_guid_generated == by_guid_committed


def test_golden_entries_validate_against_wire_v2() -> None:
    """Every golden entry validates against the extra=forbid v2 replica (round-trip)."""
    committed = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    for entry in committed:
        _WireV2Entry.model_validate(entry)


def test_golden_covers_enrolled_with_url_and_deenrolled_present() -> None:
    """The two required shapes: enrolled+resolved-URL, and de-enrolled-but-present."""
    committed = {e["guid"]: e for e in json.loads(_FIXTURE.read_text(encoding="utf-8"))}

    enrolled = committed["office-enrolled-001"]
    assert enrolled["enrolled"] is True
    assert enrolled["canonical_destination_url"] is not None
    assert enrolled["stratum"] == "trackstat"
    assert enrolled["ghl_ownership"] == "client_owned"

    deenrolled = committed["office-inactive-002"]
    assert deenrolled["enrolled"] is False  # INACTIVE
    # STILL PRESENT (in the fixture) and keeps its resolved category -- never omitted.
    assert deenrolled["stratum"] == "calendly"
    assert deenrolled["canonical_destination_url"] == "https://calendly.com/office-two"
