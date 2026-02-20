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
    build_timeline_for_offer,
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


# TestComputeTimelineEntries, TestBuildAllTimelines, and TestWarmStoryCaches
# removed per TDD-SECTION-TIMELINE-REMEDIATION: these functions were replaced
# by get_or_compute_timelines() and the compute-on-read-then-cache architecture.
# New tests for the remediated architecture will be added in the QA phase.
