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
from autom8_asana.services.scheduling_stratum_push import StratumPushResult

pytestmark = [pytest.mark.xdist_group("scheduling_normalizer")]


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

    This is the load-bearing safety: a partial office set never reaches the data
    side's whole-source DELETE.
    """
    push_called = False

    async def _enumerate() -> tuple[list[str], bool]:
        return ["only", "a", "partial"], False  # source_complete=False

    async def _push(_gids: list[str]) -> StratumPushResult:
        nonlocal push_called
        push_called = True
        return StratumPushResult(pushed=True, dry_run=False, entry_count=len(_gids), payload={})

    result = await execute_snapshot_push(
        gate=lambda: True, enumerate_office_gids=_enumerate, push=_push
    )
    assert result.status == "refused"
    assert result.entry_count == 0
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
