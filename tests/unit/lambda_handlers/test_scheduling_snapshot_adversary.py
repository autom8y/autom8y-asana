"""Adversarial QA fixtures for the I2 whole-snapshot handler (completeness + DARK).

Two-sided (RED on a deliberately-broken variant / GREEN correct). Covers:

  * (d2) PARTIAL-BATCH REFUSAL -- the whole-snapshot entry point must NEVER emit a
    completed-entities PARTIAL as a full snapshot. An incomplete source (or an empty
    batch) is REFUSED and NOTHING is pushed. A partial fed to the data side's
    whole-source DELETE would mass-wipe live enrolled offices.
  * (h) DARK-GATE -- a confused/malicious event that forces ``dry_run=False`` CANNOT
    punch through the DARK handler gate: with SCHEDULING_STRATUM_PUSH_ENABLED unset
    the handler still returns skipped (200) with ZERO substrate build.
"""

from __future__ import annotations

import pytest

from autom8_asana.lambda_handlers.scheduling_stratum_snapshot import (
    SnapshotRefusedError,
    assert_complete_office_set,
    execute_snapshot_push,
    handler,
)
from autom8_asana.normalizer.scheduling_extractor import ExtractedScheduling
from autom8_asana.normalizer.scheduling_stratum import CASCADE_PRIORITY
from autom8_asana.services.scheduling_stratum_push import StratumPushResult

pytestmark = [pytest.mark.xdist_group("scheduling_normalizer")]


def _office(guid: str) -> ExtractedScheduling:
    return ExtractedScheduling(
        guid=guid,
        normalized_inputs={**{f: None for f in CASCADE_PRIORITY}, "reviewwave_id": "rw"},
    )


# --- (d2) PARTIAL-BATCH REFUSAL -------------------------------------------------


def test_d2_incomplete_source_is_refused_at_the_gate() -> None:
    """source_complete=False -> REFUSE (an unreadable/partial source must not push)."""
    with pytest.raises(SnapshotRefusedError, match="complete snapshot"):
        assert_complete_office_set(["a", "b"], source_complete=False)


def test_d2_empty_batch_is_refused_not_pushed() -> None:
    """An empty batch fed to the whole-source DELETE wipes every office -> REFUSE."""
    with pytest.raises(SnapshotRefusedError, match="empty active-office set"):
        assert_complete_office_set([], source_complete=True)
    with pytest.raises(SnapshotRefusedError, match="empty active-office set"):
        assert_complete_office_set(None, source_complete=True)


async def test_d2_partial_source_pushes_nothing_end_to_end() -> None:
    """Through execute_snapshot_push: an incomplete source -> refused, push NEVER called.

    This is the load-bearing safety: even a NON-EMPTY office set never reaches the
    data side's whole-source DELETE when source_complete is False.
    """
    push_called = False

    async def _enumerate() -> tuple[list[ExtractedScheduling], bool]:
        return [_office("only"), _office("a"), _office("partial")], False  # source_complete=False

    async def _push(_offices: list[ExtractedScheduling]) -> StratumPushResult:
        nonlocal push_called
        push_called = True
        return StratumPushResult(pushed=True, dry_run=False, entry_count=len(_offices), payload={})

    result = await execute_snapshot_push(
        gate=lambda: True, enumerate_offices=_enumerate, push=_push
    )
    assert result.status == "refused"
    assert result.entry_count == 0
    assert push_called is False


async def test_d2_schema_lag_frame_pushes_nothing_end_to_end() -> None:
    """A SCHEMA-LAG refusal (pre-1.5.0 frame) also pushes NOTHING -- never fabricates.

    A stale-while-revalidate cache serving a pre-1.5.0 frame must REFUSE rather than
    project a fabricated (all-ACTIVE) posture into the whole-source DELETE.
    """
    push_called = False

    async def _enumerate() -> tuple[list[ExtractedScheduling], bool]:
        raise SnapshotRefusedError("frame schema pre-1.5.0: projected posture columns absent")

    async def _push(_offices: list[ExtractedScheduling]) -> StratumPushResult:
        nonlocal push_called
        push_called = True
        return StratumPushResult(pushed=True, dry_run=False, entry_count=len(_offices), payload={})

    result = await execute_snapshot_push(
        gate=lambda: True, enumerate_offices=_enumerate, push=_push
    )
    assert result.status == "refused"
    assert push_called is False


# --- (h) DARK-GATE: a forced dry_run=False cannot punch through the dark gate ----


def test_h_forced_dry_run_false_event_still_skipped_when_dark(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malicious/confused event {"dry_run": False} must NOT force a live push.

    With the push-gate unset the handler short-circuits to skipped (200) BEFORE any
    substrate construction or Asana read -- the event cannot override the DARK gate.
    """
    monkeypatch.delenv("SCHEDULING_STRATUM_PUSH_ENABLED", raising=False)
    response = handler({"dry_run": False}, context=None)
    assert response["statusCode"] == 200
    assert response["body"]["status"] == "skipped"
    assert response["body"]["reason"] == "gate_off"
