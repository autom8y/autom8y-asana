"""Unit tests for section timeline service functions.

Per TDD-SECTION-TIMELINE-001 Section 13.2: Tests for service layer
functions with mocked AsanaClient dependencies.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.models.business.activity import AccountActivity
from autom8_asana.models.business.section_timeline import (
    OfferTimelineEntry,
    SectionInterval,
)
from autom8_asana.models.common import NameGid
from autom8_asana.models.story import Story
from autom8_asana.services.section_timeline_service import (
    _build_imputed_interval,
    _build_intervals_from_stories,
    _extract_office_phone,
    _is_cross_project_noise,
    _parse_datetime,
    build_all_timelines,
    build_timeline_for_offer,
    compute_timeline_entries,
    warm_story_caches,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    """Create a UTC datetime for test data."""
    return datetime(year, month, day, hour, tzinfo=UTC)


def _make_story(
    gid: str,
    created_at: str,
    new_section_name: str | None = None,
    old_section_name: str | None = None,
    resource_subtype: str = "section_changed",
) -> Story:
    """Build a Story with section_changed data."""
    new_section = NameGid(gid="s1", name=new_section_name) if new_section_name else None
    old_section = NameGid(gid="s2", name=old_section_name) if old_section_name else None
    return Story(
        gid=gid,
        resource_subtype=resource_subtype,
        created_at=created_at,
        new_section=new_section,
        old_section=old_section,
    )


def _make_task_mock(
    gid: str,
    created_at: str = "2025-01-01T00:00:00.000Z",
    section_name: str | None = "ACTIVE",
    project_gid: str = "1143843662099250",
    office_phone: str | None = None,
) -> MagicMock:
    """Build a mock Task object suitable for get_section_timelines."""
    task = MagicMock()
    task.gid = gid
    task.created_at = created_at
    memberships = []
    if section_name:
        memberships.append(
            {
                "section": {"name": section_name},
                "project": {"gid": project_gid},
            }
        )
    task.memberships = memberships

    custom_fields = []
    if office_phone:
        custom_fields.append({"name": "Office Phone", "text_value": office_phone})
    task.model_dump.return_value = {
        "custom_fields": custom_fields,
        "memberships": memberships,
    }
    return task


# ---------------------------------------------------------------------------
# _parse_datetime
# ---------------------------------------------------------------------------


class TestParseDateTime:
    def test_iso_format(self) -> None:
        """Parses Asana ISO 8601 format."""
        result = _parse_datetime("2025-01-15T10:30:00.000Z")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    def test_none_input(self) -> None:
        """Returns None for None input."""
        assert _parse_datetime(None) is None


# ---------------------------------------------------------------------------
# _is_cross_project_noise
# ---------------------------------------------------------------------------


class TestIsCrossProjectNoise:
    def test_both_none(self) -> None:
        """AC-1.3, EC-3: Both sections unknown -> filtered."""
        story = _make_story(
            gid="s1",
            created_at="2025-01-01T00:00:00.000Z",
            new_section_name="Some Random Section",
            old_section_name="Another Random Section",
        )
        assert _is_cross_project_noise(story) is True

    def test_one_known(self) -> None:
        """AC-1.4, EC-4: One section known -> retained."""
        story = _make_story(
            gid="s1",
            created_at="2025-01-01T00:00:00.000Z",
            new_section_name="ACTIVE",
            old_section_name="Some Random Section",
        )
        assert _is_cross_project_noise(story) is False

    def test_both_known(self) -> None:
        """Both sections known -> retained."""
        story = _make_story(
            gid="s1",
            created_at="2025-01-01T00:00:00.000Z",
            new_section_name="ACTIVE",
            old_section_name="INACTIVE",
        )
        assert _is_cross_project_noise(story) is False


# ---------------------------------------------------------------------------
# _build_intervals_from_stories
# ---------------------------------------------------------------------------


class TestBuildIntervalsFromStories:
    def test_chronological(self) -> None:
        """AC-2.5: Stories sorted and intervals built correctly."""
        stories = [
            _make_story(
                "s1", "2025-01-01T00:00:00.000Z", new_section_name="ACTIVATING"
            ),
            _make_story("s2", "2025-01-05T00:00:00.000Z", new_section_name="ACTIVE"),
        ]
        intervals, count = _build_intervals_from_stories(stories)
        assert count == 2
        assert len(intervals) == 2
        assert intervals[0].section_name == "ACTIVATING"
        assert intervals[1].section_name == "ACTIVE"

    def test_closes_previous(self) -> None:
        """AC-2.5: Previous interval exited_at set to current entered_at."""
        stories = [
            _make_story(
                "s1", "2025-01-01T00:00:00.000Z", new_section_name="ACTIVATING"
            ),
            _make_story("s2", "2025-01-05T00:00:00.000Z", new_section_name="ACTIVE"),
        ]
        intervals, _ = _build_intervals_from_stories(stories)
        assert intervals[0].exited_at is not None
        assert intervals[0].exited_at == intervals[1].entered_at

    def test_last_open(self) -> None:
        """AC-2.6: Final interval has exited_at=None."""
        stories = [
            _make_story("s1", "2025-01-01T00:00:00.000Z", new_section_name="ACTIVE"),
        ]
        intervals, _ = _build_intervals_from_stories(stories)
        assert intervals[0].exited_at is None

    def test_unknown_section_warning(self) -> None:
        """AC-2.3: WARNING logged for unknown sections."""
        stories = [
            _make_story(
                "s1", "2025-01-01T00:00:00.000Z", new_section_name="ZZZZ_UNKNOWN"
            ),
        ]
        with patch(
            "autom8_asana.services.section_timeline_service.logger"
        ) as mock_logger:
            intervals, _ = _build_intervals_from_stories(stories)
        assert intervals[0].classification is None
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "unknown_section_in_timeline"

    def test_empty_stories(self) -> None:
        """Empty story list returns empty intervals."""
        intervals, count = _build_intervals_from_stories([])
        assert intervals == []
        assert count == 0


# ---------------------------------------------------------------------------
# _build_imputed_interval
# ---------------------------------------------------------------------------


class TestBuildImputedInterval:
    def test_active(self) -> None:
        """AC-3.1, AC-3.4: Imputed ACTIVE interval from task created_at."""
        created = _utc(2025, 1, 1)
        intervals = _build_imputed_interval(created, AccountActivity.ACTIVE, "ACTIVE")
        assert len(intervals) == 1
        assert intervals[0].classification == AccountActivity.ACTIVE
        assert intervals[0].entered_at == created
        assert intervals[0].exited_at is None

    def test_inactive(self) -> None:
        """AC-3.3: Imputed INACTIVE interval."""
        created = _utc(2025, 1, 1)
        intervals = _build_imputed_interval(
            created, AccountActivity.INACTIVE, "INACTIVE"
        )
        assert len(intervals) == 1
        assert intervals[0].classification == AccountActivity.INACTIVE

    def test_none_created_at(self) -> None:
        """No created_at -> empty intervals."""
        intervals = _build_imputed_interval(None, AccountActivity.ACTIVE, "ACTIVE")
        assert intervals == []


# ---------------------------------------------------------------------------
# _extract_office_phone
# ---------------------------------------------------------------------------


class TestExtractOfficePhone:
    def test_found(self) -> None:
        """Office Phone found in custom_fields."""
        data = {"custom_fields": [{"name": "Office Phone", "text_value": "555-0100"}]}
        assert _extract_office_phone(data) == "555-0100"

    def test_not_found(self) -> None:
        """Office Phone not present."""
        data = {"custom_fields": [{"name": "Other Field", "text_value": "x"}]}
        assert _extract_office_phone(data) is None

    def test_empty_custom_fields(self) -> None:
        """No custom_fields key."""
        assert _extract_office_phone({}) is None


# ---------------------------------------------------------------------------
# build_timeline_for_offer
# ---------------------------------------------------------------------------


class TestBuildTimelineForOffer:
    @pytest.mark.asyncio()
    async def test_with_stories(self) -> None:
        """FR-1, FR-2: End-to-end single offer timeline."""
        client = MagicMock()
        client.stories.list_for_task_cached_async = AsyncMock(
            return_value=[
                _make_story(
                    "s1",
                    "2025-01-01T00:00:00.000Z",
                    new_section_name="ACTIVATING",
                    old_section_name="Sales Process",
                ),
                _make_story(
                    "s2",
                    "2025-01-05T00:00:00.000Z",
                    new_section_name="ACTIVE",
                    old_section_name="ACTIVATING",
                ),
            ]
        )

        timeline = await build_timeline_for_offer(
            client=client,
            offer_gid="offer1",
            office_phone="555-0100",
            task_created_at=_utc(2024, 12, 1),
            current_section_name="ACTIVE",
            current_account_activity=AccountActivity.ACTIVE,
        )

        assert timeline.offer_gid == "offer1"
        assert timeline.office_phone == "555-0100"
        assert timeline.story_count == 2
        assert len(timeline.intervals) == 2
        assert timeline.intervals[0].section_name == "ACTIVATING"
        assert timeline.intervals[1].section_name == "ACTIVE"
        assert timeline.intervals[1].exited_at is None  # last is open

    @pytest.mark.asyncio()
    async def test_never_moved(self) -> None:
        """FR-3: Imputation when no section_changed stories."""
        client = MagicMock()
        # Return a comment story (not section_changed)
        client.stories.list_for_task_cached_async = AsyncMock(
            return_value=[
                Story(
                    gid="s1",
                    resource_subtype="comment_added",
                    created_at="2025-01-01T00:00:00.000Z",
                ),
            ]
        )

        timeline = await build_timeline_for_offer(
            client=client,
            offer_gid="offer1",
            office_phone=None,
            task_created_at=_utc(2024, 6, 1),
            current_section_name="ACTIVE",
            current_account_activity=AccountActivity.ACTIVE,
        )

        assert timeline.story_count == 0
        assert len(timeline.intervals) == 1
        assert timeline.intervals[0].section_name == "ACTIVE"
        assert timeline.intervals[0].classification == AccountActivity.ACTIVE
        assert timeline.intervals[0].entered_at == _utc(2024, 6, 1)


# ---------------------------------------------------------------------------
# get_section_timelines
# ---------------------------------------------------------------------------


class TestComputeTimelineEntries:
    """Tests for compute_timeline_entries() — pure CPU day counting."""

    def test_basic_day_counting(self) -> None:
        """FR-4: Computes active and billable days from pre-built timelines."""
        from autom8_asana.models.business.section_timeline import SectionTimeline

        timeline = SectionTimeline(
            offer_gid="offer1",
            office_phone="555-0100",
            intervals=(
                SectionInterval(
                    section_name="ACTIVE",
                    classification=AccountActivity.ACTIVE,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=None,
                ),
            ),
            task_created_at=_utc(2025, 1, 1),
            story_count=0,
        )
        offer_timelines = [("offer1", "555-0100", timeline)]

        entries = compute_timeline_entries(
            offer_timelines, date(2025, 1, 1), date(2025, 1, 10)
        )

        assert len(entries) == 1
        assert entries[0].offer_gid == "offer1"
        assert entries[0].active_section_days == 10
        assert entries[0].billable_section_days == 10

    def test_inactive_offer(self) -> None:
        """INACTIVE offers have 0 active days but may have billable days."""
        from autom8_asana.models.business.section_timeline import SectionTimeline

        timeline = SectionTimeline(
            offer_gid="offer2",
            office_phone=None,
            intervals=(
                SectionInterval(
                    section_name="INACTIVE",
                    classification=AccountActivity.INACTIVE,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=None,
                ),
            ),
            task_created_at=_utc(2025, 1, 1),
            story_count=0,
        )
        offer_timelines = [("offer2", None, timeline)]

        entries = compute_timeline_entries(
            offer_timelines, date(2025, 1, 1), date(2025, 1, 10)
        )

        assert entries[0].active_section_days == 0
        assert entries[0].billable_section_days == 0

    def test_multiple_offers(self) -> None:
        """Multiple offers computed correctly."""
        from autom8_asana.models.business.section_timeline import SectionTimeline

        t1 = SectionTimeline(
            offer_gid="a",
            office_phone=None,
            intervals=(
                SectionInterval(
                    section_name="ACTIVE",
                    classification=AccountActivity.ACTIVE,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=None,
                ),
            ),
            task_created_at=_utc(2025, 1, 1),
            story_count=0,
        )
        t2 = SectionTimeline(
            offer_gid="b",
            office_phone=None,
            intervals=(
                SectionInterval(
                    section_name="INACTIVE",
                    classification=AccountActivity.INACTIVE,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=None,
                ),
            ),
            task_created_at=_utc(2025, 1, 1),
            story_count=0,
        )
        offer_timelines = [("a", None, t1), ("b", None, t2)]

        entries = compute_timeline_entries(
            offer_timelines, date(2025, 1, 1), date(2025, 1, 10)
        )

        assert len(entries) == 2
        assert entries[0].active_section_days == 10
        assert entries[1].active_section_days == 0

    def test_empty_timelines(self) -> None:
        """Empty pre-computed list -> empty result."""
        entries = compute_timeline_entries([], date(2025, 1, 1), date(2025, 1, 10))
        assert entries == []


class TestBuildAllTimelines:
    """Tests for build_all_timelines() — warm-up phase pre-computation."""

    @pytest.mark.asyncio()
    async def test_full_pipeline(self) -> None:
        """FR-5: Enumerates tasks and builds SectionTimeline for each."""
        task1 = _make_task_mock(
            "offer1", section_name="ACTIVE", office_phone="555-0100"
        )
        task2 = _make_task_mock("offer2", section_name="INACTIVE")

        client = MagicMock()
        collect_mock = AsyncMock(return_value=[task1, task2])
        list_mock = MagicMock()
        list_mock.collect = collect_mock
        client.tasks.list_async.return_value = list_mock
        client.stories.list_for_task_cached_async = AsyncMock(return_value=[])

        timelines = await build_all_timelines(client=client)

        assert len(timelines) == 2
        gids = {t[0] for t in timelines}
        assert gids == {"offer1", "offer2"}

    @pytest.mark.asyncio()
    async def test_individual_failure(self) -> None:
        """AC-7.6: Failed offer logged, others succeed."""
        task1 = _make_task_mock("offer1", section_name="ACTIVE")
        task2 = _make_task_mock("offer2", section_name="ACTIVE")

        client = MagicMock()
        collect_mock = AsyncMock(return_value=[task1, task2])
        list_mock = MagicMock()
        list_mock.collect = collect_mock
        client.tasks.list_async.return_value = list_mock

        async def _mock_stories(gid: str, **kwargs: object) -> list[Story]:
            if gid == "offer1":
                raise RuntimeError("API failure")
            return []

        client.stories.list_for_task_cached_async = _mock_stories

        timelines = await build_all_timelines(client=client)

        assert len(timelines) == 1
        assert timelines[0][0] == "offer2"

    @pytest.mark.asyncio()
    async def test_progress_callback(self) -> None:
        """DEF-008: on_progress fires incrementally per offer."""
        tasks = [_make_task_mock(f"offer{i}", section_name="ACTIVE") for i in range(5)]

        client = MagicMock()
        collect_mock = AsyncMock(return_value=tasks)
        list_mock = MagicMock()
        list_mock.collect = collect_mock
        client.tasks.list_async.return_value = list_mock
        client.stories.list_for_task_cached_async = AsyncMock(return_value=[])

        progress_calls: list[tuple[int, int]] = []

        def on_progress(built: int, total: int) -> None:
            progress_calls.append((built, total))

        await build_all_timelines(client=client, on_progress=on_progress)

        # Should have been called 5 times (once per offer)
        assert len(progress_calls) == 5
        # All calls should have total=5
        assert all(t == 5 for _, t in progress_calls)
        # Final call should show all built
        assert progress_calls[-1][0] == 5

    @pytest.mark.asyncio()
    async def test_parallel_concurrency(self) -> None:
        """Bounded parallelism: 25 offers processed with semaphore."""
        tasks = [_make_task_mock(f"offer{i}", section_name="ACTIVE") for i in range(25)]

        client = MagicMock()
        collect_mock = AsyncMock(return_value=tasks)
        list_mock = MagicMock()
        list_mock.collect = collect_mock
        client.tasks.list_async.return_value = list_mock
        client.stories.list_for_task_cached_async = AsyncMock(return_value=[])

        timelines = await build_all_timelines(client=client)

        assert len(timelines) == 25


# ---------------------------------------------------------------------------
# warm_story_caches
# ---------------------------------------------------------------------------


class TestWarmStoryCaches:
    @pytest.mark.asyncio()
    async def test_progress(self) -> None:
        """FR-7: Progress callback invoked once after gather completes."""
        task1 = MagicMock()
        task1.gid = "offer1"
        task2 = MagicMock()
        task2.gid = "offer2"

        client = MagicMock()
        collect_mock = AsyncMock(return_value=[task1, task2])
        list_mock = MagicMock()
        list_mock.collect = collect_mock
        client.tasks.list_async.return_value = list_mock
        client.stories.list_for_task_cached_async = AsyncMock(return_value=[])

        progress_calls = []

        def on_progress(warmed: int, total: int) -> None:
            progress_calls.append((warmed, total))

        warmed, total = await warm_story_caches(client=client, on_progress=on_progress)

        assert warmed == 2
        assert total == 2
        # DEF-008: Callback fires incrementally per offer (2 offers = 2 calls)
        assert len(progress_calls) == 2
        # All calls have total=2; final shows all warmed
        assert all(t == 2 for _, t in progress_calls)
        assert progress_calls[-1][0] == 2

    @pytest.mark.asyncio()
    async def test_individual_failure(self) -> None:
        """AC-7.6: Failed warm logged, others succeed."""
        task1 = MagicMock()
        task1.gid = "offer1"
        task2 = MagicMock()
        task2.gid = "offer2"

        client = MagicMock()
        collect_mock = AsyncMock(return_value=[task1, task2])
        list_mock = MagicMock()
        list_mock.collect = collect_mock
        client.tasks.list_async.return_value = list_mock

        call_count = 0

        async def _mock_stories(gid, **kwargs):
            nonlocal call_count
            call_count += 1
            if gid == "offer1":
                raise RuntimeError("Cache failure")
            return []

        client.stories.list_for_task_cached_async = _mock_stories

        warmed, total = await warm_story_caches(client=client)

        assert total == 2
        assert warmed == 1  # Only offer2 succeeded

    @pytest.mark.asyncio()
    async def test_parallel_concurrency(self) -> None:
        """SPIKE: Semaphore(20) limits concurrency; all offers still warmed."""
        # Create 25 tasks to exceed concurrency limit
        tasks = [MagicMock() for _ in range(25)]
        for i, t in enumerate(tasks):
            t.gid = f"offer{i}"

        client = MagicMock()
        collect_mock = AsyncMock(return_value=tasks)
        list_mock = MagicMock()
        list_mock.collect = collect_mock
        client.tasks.list_async.return_value = list_mock
        client.stories.list_for_task_cached_async = AsyncMock(return_value=[])

        warmed, total = await warm_story_caches(client=client)

        assert total == 25
        assert warmed == 25
