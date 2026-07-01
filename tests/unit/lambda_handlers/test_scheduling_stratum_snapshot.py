"""Tests for the scheduling-stratum whole-snapshot push handler (I2, DEFAULT-DARK).

Locks the load-bearing safety: the EXPLICIT COMPLETENESS CONTRACT (never push a
partial to the data side's whole-source DELETE), the DEFAULT-DARK gate (skipped +
zero substrate/Asana read when SCHEDULING_STRATUM_PUSH_ENABLED is off), and the
full-office enumeration off the warmed offer frame.
"""

from __future__ import annotations

from typing import Any

import polars as pl
import pytest

from autom8_asana.lambda_handlers import scheduling_stratum_snapshot as snap
from autom8_asana.lambda_handlers.scheduling_stratum_snapshot import (
    SnapshotRefusedError,
    assert_complete_office_set,
    execute_snapshot_push,
    handler,
    run_snapshot_push_async,
)
from autom8_asana.services.scheduling_stratum_push import StratumPushResult

pytestmark = [pytest.mark.xdist_group("scheduling_normalizer")]


# --- assert_complete_office_set (COMPLETENESS CONTRACT) --------------------------


def test_complete_set_returns_full_gids() -> None:
    assert assert_complete_office_set(["a", "b", "c"], source_complete=True) == ["a", "b", "c"]


def test_complete_set_dedups_preserving_order() -> None:
    assert assert_complete_office_set(["a", "b", "a", "c", "b"], source_complete=True) == [
        "a",
        "b",
        "c",
    ]


def test_refuses_when_source_incomplete() -> None:
    """An unreadable/partial source is REFUSED -- pushing it would mass-wipe."""
    with pytest.raises(SnapshotRefusedError, match="complete snapshot"):
        assert_complete_office_set(["a", "b"], source_complete=False)


def test_refuses_empty_batch() -> None:
    """An empty batch fed to the whole-source DELETE wipes every office -> REFUSE."""
    with pytest.raises(SnapshotRefusedError, match="empty active-office set"):
        assert_complete_office_set([], source_complete=True)
    with pytest.raises(SnapshotRefusedError, match="empty active-office set"):
        assert_complete_office_set(None, source_complete=True)


def test_refuses_all_blank_gids() -> None:
    with pytest.raises(SnapshotRefusedError):
        assert_complete_office_set(["", ""], source_complete=True)


# --- execute_snapshot_push (gate + completeness + push orchestration) ------------


async def _push_ok(office_gids: list[str]) -> StratumPushResult:
    return StratumPushResult(pushed=True, dry_run=False, entry_count=len(office_gids), payload={})


async def _push_dry(office_gids: list[str]) -> StratumPushResult:
    return StratumPushResult(pushed=False, dry_run=True, entry_count=len(office_gids), payload={})


async def test_gate_off_skips_without_enumerating() -> None:
    """DEFAULT-DARK: gate off -> skipped, and the enumeration is NEVER invoked."""
    enumerate_called = False

    async def _enumerate() -> tuple[list[str], bool]:
        nonlocal enumerate_called
        enumerate_called = True
        return ["a"], True

    async def _push(_gids: list[str]) -> StratumPushResult:
        raise AssertionError("push must not run when the gate is off")

    result = await execute_snapshot_push(
        gate=lambda: False, enumerate_office_gids=_enumerate, push=_push
    )
    assert result.status == "skipped"
    assert result.reason == "gate_off"
    assert enumerate_called is False  # no substrate build, no Asana read


async def test_incomplete_source_refuses_without_pushing() -> None:
    push_called = False

    async def _enumerate() -> tuple[list[str], bool]:
        return ["a", "b"], False  # source_complete=False

    async def _push(_gids: list[str]) -> StratumPushResult:
        nonlocal push_called
        push_called = True
        return await _push_ok(_gids)

    result = await execute_snapshot_push(
        gate=lambda: True, enumerate_office_gids=_enumerate, push=_push
    )
    assert result.status == "refused"
    assert push_called is False  # NEVER push a partial


async def test_complete_source_pushes_full_set() -> None:
    pushed_gids: list[str] = []

    async def _enumerate() -> tuple[list[str], bool]:
        return ["o1", "o2", "o3"], True

    async def _push(gids: list[str]) -> StratumPushResult:
        pushed_gids.extend(gids)
        return await _push_ok(gids)

    result = await execute_snapshot_push(
        gate=lambda: True, enumerate_office_gids=_enumerate, push=_push
    )
    assert result.status == "pushed"
    assert result.entry_count == 3
    assert pushed_gids == ["o1", "o2", "o3"]


async def test_dry_run_push_reports_dry_run_status() -> None:
    async def _enumerate() -> tuple[list[str], bool]:
        return ["o1"], True

    result = await execute_snapshot_push(
        gate=lambda: True, enumerate_office_gids=_enumerate, push=_push_dry
    )
    assert result.status == "dry_run"


# --- _enumerate_active_office_gids (full offer-frame source) ---------------------


class _FakeEntry:
    def __init__(self, dataframe: Any) -> None:
        self.dataframe = dataframe


class _FakeCache:
    def __init__(self, entry: Any) -> None:
        self._entry = entry
        self.requested: tuple[str, str] | None = None

    async def get_async(self, project_gid: str, entity_type: str) -> Any:
        self.requested = (project_gid, entity_type)
        return self._entry


async def test_enumerate_reads_full_gid_column() -> None:
    df = pl.DataFrame({"gid": ["o1", "o2", "o3"], "name": ["a", "b", "c"]})
    cache = _FakeCache(_FakeEntry(df))
    gids, complete = await snap._enumerate_active_office_gids(cache, "PROJ")
    assert complete is True
    assert gids == ["o1", "o2", "o3"]
    assert cache.requested == ("PROJ", "offer")  # reads the OFFER frame (full source)


async def test_enumerate_absent_frame_is_incomplete() -> None:
    """No warmed offer frame -> source_complete=False -> the gate will REFUSE."""
    gids, complete = await snap._enumerate_active_office_gids(_FakeCache(None), "PROJ")
    assert gids == []
    assert complete is False


async def test_enumerate_frame_without_gid_column_is_incomplete() -> None:
    df = pl.DataFrame({"name": ["a"]})
    gids, complete = await snap._enumerate_active_office_gids(_FakeCache(_FakeEntry(df)), "PROJ")
    assert gids == []
    assert complete is False


# --- handler (end-to-end DARK) --------------------------------------------------


def test_handler_dark_returns_skipped_200(monkeypatch: pytest.MonkeyPatch) -> None:
    """With the gate unset the handler short-circuits to skipped (200), no substrate."""
    monkeypatch.delenv("SCHEDULING_STRATUM_PUSH_ENABLED", raising=False)
    response = handler({}, context=None)
    assert response["statusCode"] == 200
    assert response["body"]["status"] == "skipped"
    assert response["body"]["reason"] == "gate_off"


async def test_run_snapshot_push_async_dark_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SCHEDULING_STRATUM_PUSH_ENABLED", raising=False)
    result = await run_snapshot_push_async(context=None)
    assert result.status == "skipped"
