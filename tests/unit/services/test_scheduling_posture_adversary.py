"""Adversarial QA fixtures for the scheduling-posture PRODUCER pipeline (services leg).

Two-sided by construction (RED on a deliberately-broken variant / GREEN correct).
Covers:

  * (d) COMPLETENESS -- a de-enrolled (INACTIVE) office STAYS PRESENT in the emitted
    entries with enrolled=False; it is NEVER dropped from the snapshot. A dropped
    de-enrolled office fed to the data side's whole-source DELETE would silently wipe
    a live office -- strictly worse than a stale posture.
  * (f) ISOLATION -- one office's extraction failure is skipped, never aborting the
    whole snapshot; the failed office is ABSENT (not emitted as a null entry).
  * (h) DARK-GATE -- with SCHEDULING_STRATUM_PUSH_ENABLED unset, the end-to-end
    resolve+push pipeline reaches NO live POST (the data-service helper is never
    awaited); dry-run only.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from autom8_asana.normalizer.scheduling_extractor import ExtractedScheduling
from autom8_asana.normalizer.scheduling_stratum import CASCADE_PRIORITY
from autom8_asana.services import scheduling_stratum_push as push_mod
from autom8_asana.services.scheduling_stratum_push import (
    resolve_and_push_snapshot,
    resolve_office_entries,
)

pytestmark = [pytest.mark.xdist_group("scheduling_normalizer")]

_PUSH_HELPER = "autom8_asana.services.scheduling_stratum_push._push_to_data_service"


def _office(
    guid: str, *, enrolled: bool, field: str = "reviewwave_id", value: str = "rw"
) -> ExtractedScheduling:
    return ExtractedScheduling(
        guid=guid,
        normalized_inputs={**{f: None for f in CASCADE_PRIORITY}, field: value},
        enrolled=enrolled,
    )


# --- (d) COMPLETENESS: de-enrolled office STAYS PRESENT -------------------------


def test_d_deenrolled_office_stays_present_in_entries() -> None:
    """A batch of {enrolled, de-enrolled, enrolled} emits ALL THREE -- none dropped.

    The de-enrolled office is present with enrolled=False and keeps its stratum. A
    producer that omits de-enrolled offices would shrink the snapshot and mass-wipe
    live offices on the data side's whole-source DELETE.
    """
    offices = [
        _office("office-a", enrolled=True, field="reviewwave_id", value="rw-a"),
        _office(
            "office-b-inactive",
            enrolled=False,
            field="calendly_url",
            value="https://calendly.com/b",
        ),
        _office("office-c", enrolled=True, field="sked_id", value="sk-c"),
    ]
    entries = resolve_office_entries(offices)

    # HARD CONSTRAINT: entry_count is preserved -- every input office is emitted.
    assert len(entries) == 3
    by_guid = {e["guid"]: e for e in entries}
    assert set(by_guid) == {"office-a", "office-b-inactive", "office-c"}

    # The de-enrolled office is PRESENT with enrolled=False and keeps its category.
    deenrolled = by_guid["office-b-inactive"]
    assert deenrolled["enrolled"] is False
    assert deenrolled["stratum"] == "calendly"
    assert deenrolled["canonical_destination_url"] == "https://calendly.com/b"

    # The enrolled offices are enrolled=True.
    assert by_guid["office-a"]["enrolled"] is True
    assert by_guid["office-c"]["enrolled"] is True


def test_d_all_deenrolled_batch_is_not_shrunk_to_empty() -> None:
    """A batch that is ENTIRELY de-enrolled still emits every office (no shrink-to-0)."""
    offices = [
        _office("d1", enrolled=False, field="janeapp_url", value="https://office.janeapp.com/1"),
        _office("d2", enrolled=False, field="janeapp_url", value="https://office.janeapp.com/2"),
    ]
    entries = resolve_office_entries(offices)
    assert [e["guid"] for e in entries] == ["d1", "d2"]
    assert all(e["enrolled"] is False for e in entries)


# --- (f) ISOLATION: one failure never aborts the whole snapshot -----------------


async def test_f_per_office_failure_isolated_failed_office_absent() -> None:
    """One office raising is skipped; the survivors emit and the failed guid is ABSENT."""

    async def flaky_extract(gid: str, **_kw: object) -> ExtractedScheduling:
        if gid == "BOOM":
            raise RuntimeError("extract boom")
        return ExtractedScheduling(
            guid=f"guid-{gid}",
            normalized_inputs={**{f: None for f in CASCADE_PRIORITY}, "acuity_cal_url": "ac"},
        )

    result = await resolve_and_push_snapshot(
        ["O1", "BOOM", "O2"],
        client=object(),
        query_engine=object(),
        dry_run=True,
        extract_fn=flaky_extract,
    )
    # Two survivors emitted; the boom office is absent (not a null/placeholder entry).
    assert result.entry_count == 2
    emitted = {e["guid"] for e in result.payload["entries"]}
    assert emitted == {"guid-O1", "guid-O2"}
    assert "guid-BOOM" not in emitted


# --- (h) DARK-GATE: no live POST reachable end-to-end ---------------------------


async def test_h_dark_gate_no_live_post_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gate unset -> the whole resolve+push pipeline reaches NO live POST (dry-run)."""
    monkeypatch.delenv(push_mod.SCHEDULING_STRATUM_PUSH_ENABLED_ENV_VAR, raising=False)

    async def fake_extract(gid: str, **_kw: object) -> ExtractedScheduling:
        return ExtractedScheduling(
            guid=f"guid-{gid}",
            normalized_inputs={**{f: None for f in CASCADE_PRIORITY}, "custom_ghl_id": "cal-x"},
        )

    helper = AsyncMock(return_value=True)
    with patch(_PUSH_HELPER, new=helper):
        result = await resolve_and_push_snapshot(
            ["O1", "O2"],
            client=object(),
            query_engine=object(),
            extract_fn=fake_extract,
        )
    # dry-run defaulted from the OFF gate; the live POST helper was never awaited.
    assert result.dry_run is True
    assert result.pushed is False
    helper.assert_not_awaited()


async def test_h_dark_gate_holds_even_when_data_creds_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even WITH data-service creds set, an unset push-gate stays dry-run (no POST).

    Guards against a leak where credential-presence -- not the explicit gate -- drives
    the live POST decision.
    """
    monkeypatch.delenv(push_mod.SCHEDULING_STRATUM_PUSH_ENABLED_ENV_VAR, raising=False)

    async def fake_extract(gid: str, **_kw: object) -> ExtractedScheduling:
        return ExtractedScheduling(
            guid=f"guid-{gid}",
            normalized_inputs={f: None for f in CASCADE_PRIORITY},
        )

    helper = AsyncMock(return_value=True)
    with patch(_PUSH_HELPER, new=helper):
        result = await resolve_and_push_snapshot(
            ["O1"],
            client=object(),
            query_engine=object(),
            data_service_url="https://data.internal",
            auth_token="tok",  # noqa: S106 -- test stub, not a real secret
            extract_fn=fake_extract,
        )
    assert result.dry_run is True
    helper.assert_not_awaited()
