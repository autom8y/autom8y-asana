"""Tests for the scheduling-stratum snapshot push (Phase-2 normalizer-seam).

Locks the FROZEN wire contract v2 (docs/contracts/scheduling-posture-wire-v2.md):
the built entry/envelope field names match ``SchedulingStratumEntry`` /
``SchedulingStratumSyncRequest`` exactly -- v1 keys PLUS the v2 additions
``{enrolled, canonical_destination_url, ghl_ownership}`` -- validated against a local
extra=forbid replica so a stray key is caught; the DEFAULT-OFF gate (dry-run unless
explicitly enabled), the dry-run no-POST guarantee, and the live POST endpoint +
per-office isolation in the resolve+push pipeline.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel, ConfigDict, Field

from autom8_asana.normalizer.scheduling_extractor import ExtractedScheduling
from autom8_asana.normalizer.scheduling_stratum import CASCADE_PRIORITY, StratumResult
from autom8_asana.services import scheduling_stratum_push as push_mod
from autom8_asana.services.scheduling_stratum_push import (
    SNAPSHOT_SOURCE,
    build_stratum_entry,
    build_sync_payload,
    push_stratum_snapshot,
    resolve_and_push_snapshot,
    resolve_office_entries,
)

pytestmark = [pytest.mark.xdist_group("scheduling_normalizer")]

_PUSH_HELPER = "autom8_asana.services.scheduling_stratum_push._push_to_data_service"


# --- Local replica of the FROZEN wire contract v2 (extra=forbid teeth) -----------


class _WireStratumEnum(StrEnum):
    REVIEWWAVE = "reviewwave"
    ACUITY = "acuity"
    CALENDLY = "calendly"
    JANEAPP = "janeapp"
    EHR = "ehr"
    TRACKSTAT = "trackstat"
    SKED = "sked"
    GCAL = "gcal"  # RUL-22 ninth source field -> gcal plane (autom8y-data STRATUM_VALUES)
    GHL = "ghl"
    INACTIVE = "inactive"


class _WireGhlOwnership(StrEnum):
    CLIENT_OWNED = "client_owned"
    INTERNAL_DURATION = "internal_duration"
    NONE = "none"


class _WireV2Entry(BaseModel):
    """extra=forbid replica of the FROZEN wire contract v2.1 entry surface.

    v2.1 adds ONE optional field (``served_calendar_id``). It is optional (default
    None) so a flag-OFF entry that OMITS the key still validates, while a stray/unknown
    key is still rejected (extra=forbid teeth preserved).
    """

    model_config = ConfigDict(extra="forbid")
    guid: str = Field(min_length=1, max_length=36)
    stratum: _WireStratumEnum
    custom_ghl_id: str | None = Field(default=None, max_length=255)
    ghl_calendar_id: str | None = Field(default=None, max_length=255)
    resolved_at: datetime | None = None
    # v2 additions (FORK-1 Option 2)
    enrolled: bool
    canonical_destination_url: str | None = None
    ghl_ownership: _WireGhlOwnership
    # v2.1 addition (RUL-22 ninth source field) — OPTIONAL, default null.
    served_calendar_id: str | None = Field(default=None, max_length=255)


class _WireV2SyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot_source: str = "asana"
    entries: list[_WireV2Entry]
    source_timestamp: datetime
    entry_count: int = Field(ge=0)


_ENTRY_FIELDS = {
    "guid",
    "stratum",
    "custom_ghl_id",
    "ghl_calendar_id",
    "resolved_at",
    "enrolled",
    "canonical_destination_url",
    "ghl_ownership",
}
_ENVELOPE_FIELDS = {"snapshot_source", "entries", "source_timestamp", "entry_count"}


def _sample_result() -> StratumResult:
    return StratumResult(
        stratum="ghl",
        custom_ghl_id="cal-1",
        ghl_calendar_id="https://x/cal-1",
        enrolled=True,
        canonical_destination_url="https://x/cal-1",
        ghl_ownership="client_owned",
    )


# --- entry / envelope contract-match --------------------------------------------


def test_build_stratum_entry_field_names_match_pr218() -> None:
    entry = build_stratum_entry("guid-1", _sample_result(), datetime.now(UTC))
    assert set(entry) == _ENTRY_FIELDS
    # extra=forbid replica accepts it (no stray key, all types valid).
    _WireV2Entry.model_validate(entry)


def test_build_sync_payload_field_names_match_pr218() -> None:
    entry = build_stratum_entry("guid-1", _sample_result(), datetime.now(UTC))
    payload = build_sync_payload([entry], datetime.now(UTC).isoformat())
    assert set(payload) == _ENVELOPE_FIELDS
    assert payload["snapshot_source"] == SNAPSHOT_SOURCE == "asana"
    assert payload["entry_count"] == 1
    # The whole envelope validates against the extra=forbid PR #218 replica.
    _WireV2SyncRequest.model_validate(payload)


def test_envelope_only_keys_rejected_on_entry() -> None:
    """An envelope-only field on an entry would 422 the sync (extra=forbid proof)."""
    entry = build_stratum_entry("guid-1", _sample_result(), datetime.now(UTC))
    contaminated = {**entry, "snapshot_source": "asana"}  # snapshot_source is envelope-only
    with pytest.raises(ValueError, match="snapshot_source"):
        _WireV2Entry.model_validate(contaminated)


def test_entry_count_integrity_witness() -> None:
    entries = [build_stratum_entry(f"g{i}", _sample_result(), None) for i in range(3)]
    payload = build_sync_payload(entries, datetime.now(UTC).isoformat())
    assert payload["entry_count"] == len(payload["entries"]) == 3


# --- F-5: served_calendar_id emission gate (v2.1, DEFAULT-OFF omits the KEY) ------

_GCAL_ID = "c_3f7a9@group.calendar.google.com"


def _gcal_result() -> StratumResult:
    return StratumResult(
        stratum="gcal",
        custom_ghl_id=None,
        ghl_calendar_id=None,
        enrolled=True,
        canonical_destination_url=None,
        ghl_ownership="none",
        served_calendar_id=_GCAL_ID,
    )


def test_f5_flag_off_omits_served_calendar_id_key() -> None:
    """Flag OFF (default) -> the KEY is absent, not present-with-None (extra=forbid).

    ``extra="forbid"`` rejects unknown KEYS regardless of value, so a pre-migration
    data image would 422 on ``served_calendar_id=None`` just as on a real value. The
    wire must stay byte-identical to v2 when off.
    """
    entry = build_stratum_entry("g1", _gcal_result(), datetime.now(UTC))
    assert "served_calendar_id" not in entry
    assert set(entry) == _ENTRY_FIELDS
    _WireV2Entry.model_validate(entry)


def test_f5_flag_on_includes_served_calendar_id_value() -> None:
    """Flag ON -> the key is present and carries the identity; v2.1 replica accepts it."""
    entry = build_stratum_entry(
        "g1", _gcal_result(), datetime.now(UTC), emit_served_calendar_id=True
    )
    assert "served_calendar_id" in entry
    assert entry["served_calendar_id"] == _GCAL_ID
    assert set(entry) == _ENTRY_FIELDS | {"served_calendar_id"}
    _WireV2Entry.model_validate(entry)


def test_f5_resolve_office_entries_defaults_to_env_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """resolve_office_entries defers to SCHEDULING_STRATUM_SERVED_CALENDAR_ID_ENABLED.

    Unset -> omit; truthy -> include. Two-sided over the SAME office so only the gate
    differs.
    """
    office = ExtractedScheduling(
        guid="g-gcal",
        normalized_inputs={**{f: None for f in CASCADE_PRIORITY}, "google_cal_id": _GCAL_ID},
    )

    monkeypatch.delenv(
        push_mod.SCHEDULING_STRATUM_SERVED_CALENDAR_ID_ENABLED_ENV_VAR, raising=False
    )
    (off_entry,) = resolve_office_entries([office])
    assert "served_calendar_id" not in off_entry

    monkeypatch.setenv(push_mod.SCHEDULING_STRATUM_SERVED_CALENDAR_ID_ENABLED_ENV_VAR, "true")
    (on_entry,) = resolve_office_entries([office])
    assert on_entry["served_calendar_id"] == _GCAL_ID
    assert on_entry["stratum"] == "gcal"


# --- resolve_office_entries (pure dry-run pipeline) ------------------------------


def test_resolve_office_entries_resolves_strata() -> None:
    offices = [
        ExtractedScheduling(
            guid="g-rw",
            normalized_inputs={**{f: None for f in CASCADE_PRIORITY}, "reviewwave_id": "rw"},
        ),
        ExtractedScheduling(
            guid="g-inactive",
            normalized_inputs={f: None for f in CASCADE_PRIORITY},
        ),
    ]
    entries = resolve_office_entries(offices)
    assert [e["stratum"] for e in entries] == ["reviewwave", "inactive"]
    assert [e["guid"] for e in entries] == ["g-rw", "g-inactive"]
    for e in entries:
        _WireV2Entry.model_validate(e)


def test_resolve_office_entries_threads_enrolled_and_ownership() -> None:
    """The extractor's v2 axes (enrolled / ghl_ownership) ride onto the built entry.

    A de-enrolled office is PRESENT in the batch with ``enrolled=False`` -- never
    omitted (the enrolled-bit HARD CONSTRAINT) -- and keeps its resolved category.
    """
    offices = [
        ExtractedScheduling(
            guid="g-off",
            normalized_inputs={**{f: None for f in CASCADE_PRIORITY}, "sked_id": "sk-1"},
            enrolled=False,
            ghl_ownership="client_owned",
        ),
    ]
    entries = resolve_office_entries(offices)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["enrolled"] is False  # de-enrolled but PRESENT
    assert entry["stratum"] == "sked"  # orthogonal: category preserved
    assert entry["canonical_destination_url"] == "https://portal.sked.life/new-patient?key=sk-1"
    assert entry["ghl_ownership"] == "client_owned"
    _WireV2Entry.model_validate(entry)


# --- push gating + dry-run ------------------------------------------------------


async def test_push_dry_run_builds_payload_no_post() -> None:
    entry = build_stratum_entry("g1", _sample_result(), datetime.now(UTC))
    helper = AsyncMock()
    with patch(_PUSH_HELPER, new=helper):
        result = await push_stratum_snapshot([entry], datetime.now(UTC).isoformat(), dry_run=True)
    assert result.dry_run is True
    assert result.pushed is False
    assert set(result.payload) == _ENVELOPE_FIELDS
    helper.assert_not_awaited()


async def test_push_default_gate_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset gate -> dry-run by default (no live POST)."""
    monkeypatch.delenv(push_mod.SCHEDULING_STRATUM_PUSH_ENABLED_ENV_VAR, raising=False)
    entry = build_stratum_entry("g1", _sample_result(), datetime.now(UTC))
    helper = AsyncMock()
    with patch(_PUSH_HELPER, new=helper):
        result = await push_stratum_snapshot([entry], datetime.now(UTC).isoformat())
    assert result.dry_run is True
    helper.assert_not_awaited()


async def test_push_live_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(push_mod.SCHEDULING_STRATUM_PUSH_ENABLED_ENV_VAR, "true")
    entry = build_stratum_entry("g1", _sample_result(), datetime.now(UTC))
    helper = AsyncMock(return_value=True)
    with patch(_PUSH_HELPER, new=helper):
        result = await push_stratum_snapshot(
            [entry],
            datetime.now(UTC).isoformat(),
            data_service_url="https://data.internal",
            auth_token="tok",  # noqa: S106 -- test stub, not a real secret
        )
    assert result.pushed is True
    assert result.dry_run is False
    helper.assert_awaited_once()
    assert helper.await_args.kwargs["endpoint_path"] == "/api/v1/scheduling-stratum/sync"


# --- resolve_and_push_snapshot pipeline (frame-first: pre-extracted offices) ------


def _office(guid: str, *, field: str = "acuity_cal_url", value: str = "ac") -> ExtractedScheduling:
    return ExtractedScheduling(
        guid=guid,
        normalized_inputs={**{f: None for f in CASCADE_PRIORITY}, field: value},
    )


async def test_resolve_and_push_dry_run_over_extracted_offices() -> None:
    """FRAME-FIRST: the push path consumes pre-extracted offices (NO GFR loop, no client).

    The per-gid GFR loop is DELETED from the push path; offices are projected upstream
    from the warmed frame. This is a pure resolve/build/dry-run over the projected rows.
    """
    result = await resolve_and_push_snapshot(
        [_office("guid-O1"), _office("guid-O2")],
        dry_run=True,
    )
    assert result.dry_run is True
    assert result.entry_count == 2
    assert all(e["stratum"] == "acuity" for e in result.payload["entries"])


async def test_resolve_and_push_emits_all_provided_offices() -> None:
    """The pure push path emits EVERY provided office (guid-dedup/isolation is upstream).

    Per-office isolation + guid-dedup now live in the frame projection
    (``project_posture_rows``); by the time the push path runs, the offices are the
    clean deduped set and are all emitted (entry_count preserved for the whole-source
    DELETE integrity witness).
    """
    result = await resolve_and_push_snapshot(
        [_office("guid-O1"), _office("guid-O2", field="sked_id", value="sk")],
        dry_run=True,
    )
    assert result.entry_count == 2
    assert {e["guid"] for e in result.payload["entries"]} == {"guid-O1", "guid-O2"}
