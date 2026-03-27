"""Unit tests for StageTransitionRecord, EntityStageTimeline, and StageTransitionEmitter.

Test IDs: UT-OBS-001 through UT-OBS-006 from the ADR QA checklist.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from autom8_asana.lifecycle.observation import (
    EntityStageTimeline,
    StageTransitionEmitter,
    StageTransitionRecord,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_record(
    entity_gid: str = "gid1",
    entity_type: str = "Process",
    from_stage: str | None = "sales",
    to_stage: str = "onboarding",
    pipeline_stage_num: int = 3,
    transition_type: str = "converted",
    entered_at: datetime | None = None,
    exited_at: datetime | None = None,
    business_gid: str | None = "biz1",
    automation_result_id: str | None = "rule_1",
    duration_ms: float | None = 150.0,
) -> StageTransitionRecord:
    """Factory for StageTransitionRecord with sensible defaults."""
    return StageTransitionRecord(
        entity_gid=entity_gid,
        entity_type=entity_type,
        business_gid=business_gid,
        from_stage=from_stage,
        to_stage=to_stage,
        pipeline_stage_num=pipeline_stage_num,
        transition_type=transition_type,
        entered_at=entered_at or datetime(2026, 1, 15, tzinfo=UTC),
        exited_at=exited_at,
        automation_result_id=automation_result_id,
        duration_ms=duration_ms,
    )


# ---------------------------------------------------------------------------
# StageTransitionRecord tests
# ---------------------------------------------------------------------------


class TestStageTransitionRecord:
    """Test StageTransitionRecord construction and immutability."""

    def test_basic_creation(self) -> None:
        record = _make_record()
        assert record.entity_gid == "gid1"
        assert record.entity_type == "Process"
        assert record.from_stage == "sales"
        assert record.to_stage == "onboarding"
        assert record.transition_type == "converted"

    def test_frozen(self) -> None:
        record = _make_record()
        with pytest.raises(AttributeError):
            record.entity_gid = "changed"  # type: ignore[misc]

    def test_initial_transition_has_none_from_stage(self) -> None:
        record = _make_record(from_stage=None, transition_type="initial")
        assert record.from_stage is None
        assert record.transition_type == "initial"

    def test_nullable_fields(self) -> None:
        record = _make_record(
            business_gid=None,
            exited_at=None,
            automation_result_id=None,
            duration_ms=None,
        )
        assert record.business_gid is None
        assert record.exited_at is None
        assert record.automation_result_id is None
        assert record.duration_ms is None


# ---------------------------------------------------------------------------
# EntityStageTimeline tests
# ---------------------------------------------------------------------------


class TestEntityStageTimeline:
    """Test EntityStageTimeline computed properties."""

    def _make_timeline(
        self, intervals: list[StageTransitionRecord]
    ) -> EntityStageTimeline:
        return EntityStageTimeline(
            entity_gid="gid1",
            entity_type="Process",
            business_gid="biz1",
            intervals=tuple(intervals),
        )

    def test_time_in_stage_single_completed_interval(self) -> None:
        """UT-OBS-002: time_in_stage returns correct delta for completed interval."""
        record = _make_record(
            to_stage="sales",
            entered_at=datetime(2026, 1, 1, tzinfo=UTC),
            exited_at=datetime(2026, 1, 11, tzinfo=UTC),
        )
        timeline = self._make_timeline([record])
        result = timeline.time_in_stage("sales")
        assert result is not None
        assert result.days == 10

    def test_time_in_stage_multiple_intervals(self) -> None:
        """UT-OBS-002: time_in_stage sums across multiple completed intervals."""
        r1 = _make_record(
            to_stage="sales",
            entered_at=datetime(2026, 1, 1, tzinfo=UTC),
            exited_at=datetime(2026, 1, 6, tzinfo=UTC),
        )
        r2 = _make_record(
            to_stage="sales",
            entered_at=datetime(2026, 2, 1, tzinfo=UTC),
            exited_at=datetime(2026, 2, 4, tzinfo=UTC),
        )
        timeline = self._make_timeline([r1, r2])
        result = timeline.time_in_stage("sales")
        assert result is not None
        assert result.days == 8

    def test_time_in_stage_open_interval_excluded(self) -> None:
        """UT-OBS-002: open intervals (exited_at=None) are not counted."""
        record = _make_record(
            to_stage="sales",
            entered_at=datetime(2026, 1, 1, tzinfo=UTC),
            exited_at=None,
        )
        timeline = self._make_timeline([record])
        assert timeline.time_in_stage("sales") is None

    def test_time_in_stage_nonexistent(self) -> None:
        """UT-OBS-002: returns None for stage with no intervals."""
        record = _make_record(to_stage="sales")
        timeline = self._make_timeline([record])
        assert timeline.time_in_stage("onboarding") is None

    def test_current_stage_returns_last_open(self) -> None:
        """UT-OBS-003: current_stage returns last interval with exited_at=None."""
        r1 = _make_record(
            to_stage="sales",
            entered_at=datetime(2026, 1, 1, tzinfo=UTC),
            exited_at=datetime(2026, 1, 10, tzinfo=UTC),
        )
        r2 = _make_record(
            to_stage="onboarding",
            entered_at=datetime(2026, 1, 10, tzinfo=UTC),
            exited_at=None,
        )
        timeline = self._make_timeline([r1, r2])
        assert timeline.current_stage() == "onboarding"

    def test_current_stage_all_closed(self) -> None:
        """UT-OBS-003: returns None when all intervals are closed."""
        record = _make_record(
            to_stage="sales",
            entered_at=datetime(2026, 1, 1, tzinfo=UTC),
            exited_at=datetime(2026, 1, 10, tzinfo=UTC),
        )
        timeline = self._make_timeline([record])
        assert timeline.current_stage() is None

    def test_days_in_current_stage(self) -> None:
        """UT-OBS-004: days_in_current_stage computes from entered_at to now."""
        entered = datetime.now(UTC) - timedelta(days=15)
        record = _make_record(
            to_stage="implementation",
            entered_at=entered,
            exited_at=None,
        )
        timeline = self._make_timeline([record])
        assert timeline.days_in_current_stage() == 15

    def test_days_in_current_stage_no_open(self) -> None:
        """UT-OBS-004: returns 0 when no open interval."""
        record = _make_record(
            to_stage="sales",
            entered_at=datetime(2026, 1, 1, tzinfo=UTC),
            exited_at=datetime(2026, 1, 10, tzinfo=UTC),
        )
        timeline = self._make_timeline([record])
        assert timeline.days_in_current_stage() == 0

    def test_converted_through_success(self) -> None:
        """Entity that converted through sales -> onboarding -> implementation."""
        r1 = _make_record(to_stage="sales", transition_type="converted")
        r2 = _make_record(to_stage="onboarding", transition_type="converted")
        r3 = _make_record(to_stage="implementation", transition_type="converted")
        timeline = self._make_timeline([r1, r2, r3])
        assert timeline.converted_through(["sales", "onboarding", "implementation"])

    def test_converted_through_partial(self) -> None:
        """Entity that only converted through sales -- not through onboarding."""
        r1 = _make_record(to_stage="sales", transition_type="converted")
        r2 = _make_record(to_stage="outreach", transition_type="did_not_convert")
        timeline = self._make_timeline([r1, r2])
        assert not timeline.converted_through(["sales", "onboarding"])

    def test_converted_through_empty_stages(self) -> None:
        """Empty stages list always returns True."""
        timeline = self._make_timeline([])
        assert timeline.converted_through([])

    def test_converted_through_ignores_non_converted(self) -> None:
        """Only counts transitions with type='converted'."""
        r1 = _make_record(to_stage="sales", transition_type="did_not_convert")
        timeline = self._make_timeline([r1])
        assert not timeline.converted_through(["sales"])


# ---------------------------------------------------------------------------
# StageTransitionEmitter tests
# ---------------------------------------------------------------------------


class TestStageTransitionEmitter:
    """Test StageTransitionEmitter fire-and-forget behavior."""

    def test_emit_calls_store_append(self) -> None:
        """UT-OBS-005: emitter calls store.append on successful emit."""
        store = MagicMock()
        emitter = StageTransitionEmitter(store=store)
        record = _make_record()

        asyncio.get_event_loop().run_until_complete(emitter.emit(record))
        store.append.assert_called_once_with(record)

    def test_emit_swallows_store_exception(self) -> None:
        """UT-OBS-005: emitter does not propagate store exceptions."""
        store = MagicMock()
        store.append.side_effect = OSError("disk full")
        emitter = StageTransitionEmitter(store=store)
        record = _make_record()

        # Should not raise
        asyncio.get_event_loop().run_until_complete(emitter.emit(record))
        store.append.assert_called_once()
