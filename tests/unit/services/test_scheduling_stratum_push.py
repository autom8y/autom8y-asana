"""Tests for the scheduling-stratum snapshot push (Phase-2 normalizer-seam).

Locks the Phase-1 (PR #218) CONTRACT: the built entry/envelope field names match
``SchedulingStratumEntry`` / ``SchedulingStratumSyncRequest`` exactly (validated
against a local extra=forbid replica so a stray key is caught), the DEFAULT-OFF gate
(dry-run unless explicitly enabled), the dry-run no-POST guarantee, and the live
POST endpoint + per-office isolation in the resolve+push pipeline.
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


# --- Local replica of the Phase-1 PR #218 contract (extra=forbid teeth) ----------


class _Pr218StratumEnum(StrEnum):
    REVIEWWAVE = "reviewwave"
    ACUITY = "acuity"
    CALENDLY = "calendly"
    JANEAPP = "janeapp"
    EHR = "ehr"
    TRACKSTAT = "trackstat"
    SKED = "sked"
    GHL = "ghl"
    INACTIVE = "inactive"


class _Pr218Entry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    guid: str = Field(min_length=1, max_length=36)
    stratum: _Pr218StratumEnum
    custom_ghl_id: str | None = Field(default=None, max_length=255)
    ghl_calendar_id: str | None = Field(default=None, max_length=255)
    resolved_at: datetime | None = None


class _Pr218SyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot_source: str = "asana"
    entries: list[_Pr218Entry]
    source_timestamp: datetime
    entry_count: int = Field(ge=0)


_ENTRY_FIELDS = {"guid", "stratum", "custom_ghl_id", "ghl_calendar_id", "resolved_at"}
_ENVELOPE_FIELDS = {"snapshot_source", "entries", "source_timestamp", "entry_count"}


def _sample_result() -> StratumResult:
    return StratumResult(stratum="ghl", custom_ghl_id="cal-1", ghl_calendar_id="https://x/cal-1")


# --- entry / envelope contract-match --------------------------------------------


def test_build_stratum_entry_field_names_match_pr218() -> None:
    entry = build_stratum_entry("guid-1", _sample_result(), datetime.now(UTC))
    assert set(entry) == _ENTRY_FIELDS
    # extra=forbid replica accepts it (no stray key, all types valid).
    _Pr218Entry.model_validate(entry)


def test_build_sync_payload_field_names_match_pr218() -> None:
    entry = build_stratum_entry("guid-1", _sample_result(), datetime.now(UTC))
    payload = build_sync_payload([entry], datetime.now(UTC).isoformat())
    assert set(payload) == _ENVELOPE_FIELDS
    assert payload["snapshot_source"] == SNAPSHOT_SOURCE == "asana"
    assert payload["entry_count"] == 1
    # The whole envelope validates against the extra=forbid PR #218 replica.
    _Pr218SyncRequest.model_validate(payload)


def test_envelope_only_keys_rejected_on_entry() -> None:
    """An envelope-only field on an entry would 422 the sync (extra=forbid proof)."""
    entry = build_stratum_entry("guid-1", _sample_result(), datetime.now(UTC))
    contaminated = {**entry, "snapshot_source": "asana"}  # snapshot_source is envelope-only
    with pytest.raises(ValueError, match="snapshot_source"):
        _Pr218Entry.model_validate(contaminated)


def test_entry_count_integrity_witness() -> None:
    entries = [build_stratum_entry(f"g{i}", _sample_result(), None) for i in range(3)]
    payload = build_sync_payload(entries, datetime.now(UTC).isoformat())
    assert payload["entry_count"] == len(payload["entries"]) == 3


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
        _Pr218Entry.model_validate(e)


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


# --- resolve_and_push_snapshot pipeline -----------------------------------------


async def test_resolve_and_push_dry_run_with_injected_extractor() -> None:
    async def fake_extract(gid: str, **_kw: object) -> ExtractedScheduling:
        return ExtractedScheduling(
            guid=f"guid-{gid}",
            normalized_inputs={**{f: None for f in CASCADE_PRIORITY}, "acuity_cal_url": "ac"},
        )

    result = await resolve_and_push_snapshot(
        ["O1", "O2"],
        client=object(),
        query_engine=object(),
        dry_run=True,
        extract_fn=fake_extract,
    )
    assert result.dry_run is True
    assert result.entry_count == 2
    assert all(e["stratum"] == "acuity" for e in result.payload["entries"])


async def test_resolve_and_push_isolates_per_office_failure() -> None:
    async def flaky_extract(gid: str, **_kw: object) -> ExtractedScheduling:
        if gid == "BAD":
            raise RuntimeError("extract boom")
        return ExtractedScheduling(
            guid=f"guid-{gid}",
            normalized_inputs={**{f: None for f in CASCADE_PRIORITY}, "sked_id": "sk"},
        )

    result = await resolve_and_push_snapshot(
        ["O1", "BAD", "O2"],
        client=object(),
        query_engine=object(),
        dry_run=True,
        extract_fn=flaky_extract,
    )
    # The failed office is skipped, not fatal.
    assert result.entry_count == 2
    assert {e["guid"] for e in result.payload["entries"]} == {"guid-O1", "guid-O2"}
