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
    _extract_offer_id,
    _extract_office_phone,
    _is_cross_project_noise,
    _parse_datetime,
    build_timeline_for_offer,
    get_or_compute_timelines,
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
    offer_id: str | None = None,
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
    if offer_id is not None:
        custom_fields.append({"name": "Offer ID", "text_value": offer_id})
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
            _make_story("s1", "2025-01-01T00:00:00.000Z", new_section_name="ACTIVATING"),
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
            _make_story("s1", "2025-01-01T00:00:00.000Z", new_section_name="ACTIVATING"),
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
            _make_story("s1", "2025-01-01T00:00:00.000Z", new_section_name="ZZZZ_UNKNOWN"),
        ]
        with patch("autom8_asana.services.section_timeline_service.logger") as mock_logger:
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
        intervals = _build_imputed_interval(created, AccountActivity.INACTIVE, "INACTIVE")
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
# _extract_offer_id
# ---------------------------------------------------------------------------


class TestExtractOfferId:
    def test_found(self) -> None:
        """Offer ID found in custom_fields."""
        data = {"custom_fields": [{"name": "Offer ID", "text_value": "OFR-1234"}]}
        assert _extract_offer_id(data) == "OFR-1234"

    def test_not_found(self) -> None:
        """Offer ID not present."""
        data = {"custom_fields": [{"name": "Other Field", "text_value": "x"}]}
        assert _extract_offer_id(data) is None

    def test_empty_custom_fields(self) -> None:
        """No custom_fields key."""
        assert _extract_offer_id({}) is None

    def test_empty_string_normalized_to_none(self) -> None:
        """DD-1: Empty string text_value normalized to None."""
        data = {"custom_fields": [{"name": "Offer ID", "text_value": ""}]}
        assert _extract_offer_id(data) is None

    def test_none_text_value_returns_none(self) -> None:
        """EC-3: text_value=None returns None."""
        data = {"custom_fields": [{"name": "Offer ID", "text_value": None}]}
        assert _extract_offer_id(data) is None

    def test_non_dict_entries_skipped(self) -> None:
        """EC-8: Non-dict entries in custom_fields are skipped."""
        data = {"custom_fields": ["not_a_dict", 42, None]}
        assert _extract_offer_id(data) is None


# ---------------------------------------------------------------------------
# build_timeline_for_offer
# ---------------------------------------------------------------------------


class TestBuildTimelineForOffer:
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
            offer_id="OFR-TEST",
            task_created_at=_utc(2024, 12, 1),
            current_section_name="ACTIVE",
            current_account_activity=AccountActivity.ACTIVE,
        )

        assert timeline.offer_gid == "offer1"
        assert timeline.office_phone == "555-0100"
        assert timeline.offer_id == "OFR-TEST"
        assert timeline.story_count == 2
        assert len(timeline.intervals) == 2
        assert timeline.intervals[0].section_name == "ACTIVATING"
        assert timeline.intervals[1].section_name == "ACTIVE"
        assert timeline.intervals[1].exited_at is None  # last is open

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
            offer_id=None,
            task_created_at=_utc(2024, 6, 1),
            current_section_name="ACTIVE",
            current_account_activity=AccountActivity.ACTIVE,
        )

        assert timeline.offer_id is None
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


# ---------------------------------------------------------------------------
# _compute_day_counts: S-3 (current_section/classification) + S-1 (filter)  # noqa: ERA001
# ---------------------------------------------------------------------------


from autom8_asana.models.business.activity import OFFER_CLASSIFIER, SectionClassifier
from autom8_asana.models.business.section_timeline import SectionTimeline
from autom8_asana.services.section_timeline_service import _compute_day_counts


def _build_timeline(
    offer_gid: str,
    intervals: tuple[SectionInterval, ...],
    office_phone: str | None = None,
    offer_id: str | None = None,
) -> SectionTimeline:
    """Helper to build SectionTimeline for _compute_day_counts tests."""
    return SectionTimeline(
        offer_gid=offer_gid,
        office_phone=office_phone,
        offer_id=offer_id,
        intervals=intervals,
        task_created_at=_utc(2025, 1, 1),
        story_count=len(intervals),
    )


class TestComputeDayCountsCurrentFields:
    """S-3: _compute_day_counts populates current_section and current_classification."""

    def test_derives_current_section_from_last_interval(self) -> None:
        """current_section is the section_name of the last interval."""
        tl = _build_timeline(
            "offer1",
            intervals=(
                SectionInterval(
                    section_name="ACTIVATING",
                    classification=AccountActivity.ACTIVATING,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=_utc(2025, 1, 5),
                ),
                SectionInterval(
                    section_name="ACTIVE",
                    classification=AccountActivity.ACTIVE,
                    entered_at=_utc(2025, 1, 5),
                    exited_at=None,
                ),
            ),
        )
        entries = _compute_day_counts(
            [tl],
            date(2025, 1, 1),
            date(2025, 1, 10),
            classifier=OFFER_CLASSIFIER,
        )
        assert len(entries) == 1
        assert entries[0].current_section == "ACTIVE"

    def test_derives_current_classification_via_classifier(self) -> None:
        """current_classification is the string value from classifier."""
        tl = _build_timeline(
            "offer1",
            intervals=(
                SectionInterval(
                    section_name="ACTIVATING",
                    classification=AccountActivity.ACTIVATING,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=None,
                ),
            ),
        )
        entries = _compute_day_counts(
            [tl],
            date(2025, 1, 1),
            date(2025, 1, 10),
            classifier=OFFER_CLASSIFIER,
        )
        assert entries[0].current_classification == "activating"

    def test_empty_intervals_yields_none(self) -> None:
        """Empty intervals produce None for both current_* fields."""
        tl = _build_timeline("offer1", intervals=())
        entries = _compute_day_counts(
            [tl],
            date(2025, 1, 1),
            date(2025, 1, 10),
            classifier=OFFER_CLASSIFIER,
        )
        assert len(entries) == 1
        assert entries[0].current_section is None
        assert entries[0].current_classification is None

    def test_unknown_section_yields_none_classification(self) -> None:
        """A section unknown to the classifier yields None classification."""
        tl = _build_timeline(
            "offer1",
            intervals=(
                SectionInterval(
                    section_name="TOTALLY_UNKNOWN_SECTION",
                    classification=None,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=None,
                ),
            ),
        )
        entries = _compute_day_counts(
            [tl],
            date(2025, 1, 1),
            date(2025, 1, 10),
            classifier=OFFER_CLASSIFIER,
        )
        assert entries[0].current_section == "TOTALLY_UNKNOWN_SECTION"
        assert entries[0].current_classification is None

    def test_classification_is_string_value(self) -> None:
        """current_classification is a plain string, not an enum object."""
        tl = _build_timeline(
            "offer1",
            intervals=(
                SectionInterval(
                    section_name="INACTIVE",
                    classification=AccountActivity.INACTIVE,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=None,
                ),
            ),
        )
        entries = _compute_day_counts(
            [tl],
            date(2025, 1, 1),
            date(2025, 1, 10),
            classifier=OFFER_CLASSIFIER,
        )
        assert isinstance(entries[0].current_classification, str)
        assert entries[0].current_classification == "inactive"

    def test_offer_id_passthrough(self) -> None:
        """offer_id from SectionTimeline is passed through to OfferTimelineEntry."""
        tl = _build_timeline(
            "offer1",
            intervals=(
                SectionInterval(
                    section_name="ACTIVE",
                    classification=AccountActivity.ACTIVE,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=None,
                ),
            ),
            offer_id="OFR-1234",
        )
        entries = _compute_day_counts(
            [tl],
            date(2025, 1, 1),
            date(2025, 1, 10),
            classifier=OFFER_CLASSIFIER,
        )
        assert entries[0].offer_id == "OFR-1234"

    def test_offer_id_none_passthrough(self) -> None:
        """offer_id=None from SectionTimeline is passed through as None."""
        tl = _build_timeline(
            "offer1",
            intervals=(
                SectionInterval(
                    section_name="ACTIVE",
                    classification=AccountActivity.ACTIVE,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=None,
                ),
            ),
            offer_id=None,
        )
        entries = _compute_day_counts(
            [tl],
            date(2025, 1, 1),
            date(2025, 1, 10),
            classifier=OFFER_CLASSIFIER,
        )
        assert entries[0].offer_id is None

    def test_no_classifier_falls_back_to_interval_classification(self) -> None:
        """Without a classifier, use the interval's stored classification."""
        tl = _build_timeline(
            "offer1",
            intervals=(
                SectionInterval(
                    section_name="ACTIVE",
                    classification=AccountActivity.ACTIVE,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=None,
                ),
            ),
        )
        entries = _compute_day_counts(
            [tl],
            date(2025, 1, 1),
            date(2025, 1, 10),
            classifier=None,
        )
        assert entries[0].current_section == "ACTIVE"
        assert entries[0].current_classification == "active"


class TestComputeDayCountsClassificationFilter:
    """S-1: _compute_day_counts filters by classification_filter."""

    def _build_mixed_timelines(self) -> list[SectionTimeline]:
        """Build a list with ACTIVE, ACTIVATING, INACTIVE, and unknown entries."""
        return [
            _build_timeline(
                "active_offer",
                intervals=(
                    SectionInterval(
                        section_name="ACTIVE",
                        classification=AccountActivity.ACTIVE,
                        entered_at=_utc(2025, 1, 1),
                        exited_at=None,
                    ),
                ),
            ),
            _build_timeline(
                "activating_offer",
                intervals=(
                    SectionInterval(
                        section_name="ACTIVATING",
                        classification=AccountActivity.ACTIVATING,
                        entered_at=_utc(2025, 1, 1),
                        exited_at=None,
                    ),
                ),
            ),
            _build_timeline(
                "inactive_offer",
                intervals=(
                    SectionInterval(
                        section_name="INACTIVE",
                        classification=AccountActivity.INACTIVE,
                        entered_at=_utc(2025, 1, 1),
                        exited_at=None,
                    ),
                ),
            ),
            _build_timeline(
                "unknown_offer",
                intervals=(
                    SectionInterval(
                        section_name="UNKNOWN_SECTION",
                        classification=None,
                        entered_at=_utc(2025, 1, 1),
                        exited_at=None,
                    ),
                ),
            ),
        ]

    def test_filter_active_only(self) -> None:
        """classification=active returns only ACTIVE entries."""
        timelines = self._build_mixed_timelines()
        entries = _compute_day_counts(
            timelines,
            date(2025, 1, 1),
            date(2025, 1, 10),
            classifier=OFFER_CLASSIFIER,
            classification_filter="active",
        )
        assert len(entries) == 1
        assert entries[0].offer_gid == "active_offer"
        assert entries[0].current_classification == "active"

    def test_filter_inactive_only(self) -> None:
        """classification=inactive returns only INACTIVE entries."""
        timelines = self._build_mixed_timelines()
        entries = _compute_day_counts(
            timelines,
            date(2025, 1, 1),
            date(2025, 1, 10),
            classifier=OFFER_CLASSIFIER,
            classification_filter="inactive",
        )
        assert len(entries) == 1
        assert entries[0].offer_gid == "inactive_offer"
        assert entries[0].current_classification == "inactive"

    def test_filter_activating_only(self) -> None:
        """classification=activating returns only ACTIVATING entries."""
        timelines = self._build_mixed_timelines()
        entries = _compute_day_counts(
            timelines,
            date(2025, 1, 1),
            date(2025, 1, 10),
            classifier=OFFER_CLASSIFIER,
            classification_filter="activating",
        )
        assert len(entries) == 1
        assert entries[0].offer_gid == "activating_offer"

    def test_no_filter_returns_all(self) -> None:
        """No classification_filter returns all entries."""
        timelines = self._build_mixed_timelines()
        entries = _compute_day_counts(
            timelines,
            date(2025, 1, 1),
            date(2025, 1, 10),
            classifier=OFFER_CLASSIFIER,
            classification_filter=None,
        )
        assert len(entries) == 4

    def test_filter_with_no_matches_returns_empty(self) -> None:
        """Filter value that matches nothing returns empty list."""
        timelines = self._build_mixed_timelines()
        entries = _compute_day_counts(
            timelines,
            date(2025, 1, 1),
            date(2025, 1, 10),
            classifier=OFFER_CLASSIFIER,
            classification_filter="ignored",
        )
        assert len(entries) == 0

    def test_filtered_count_less_than_total(self) -> None:
        """Filtered result count is strictly less than total for mixed data."""
        timelines = self._build_mixed_timelines()
        all_entries = _compute_day_counts(
            timelines,
            date(2025, 1, 1),
            date(2025, 1, 10),
            classifier=OFFER_CLASSIFIER,
            classification_filter=None,
        )
        active_entries = _compute_day_counts(
            timelines,
            date(2025, 1, 1),
            date(2025, 1, 10),
            classifier=OFFER_CLASSIFIER,
            classification_filter="active",
        )
        assert len(active_entries) < len(all_entries)


# ---------------------------------------------------------------------------
# Scale-boundary regression test (SCAR-015)
# ---------------------------------------------------------------------------


class TestScaleBoundary:
    """Regression test for SCAR-015: timeline 504 at ~3,800 offers.

    The production incident occurred when per-request I/O exceeded the ALB
    60-second timeout. The remediation moved I/O to warm-up, making the
    request handler pure-CPU. This test asserts the CPU-bound timeline
    building phase stays well under the timeout threshold at production
    scale.

    The test exercises the full Step 5 hot loop (model_dump, story parsing,
    interval building, imputation) with 4,000 synthetic tasks — above the
    ~3,800 production scale that triggered SCAR-015.
    """

    async def test_timeline_computation_under_threshold_at_production_scale(
        self,
    ) -> None:
        """SCAR-015 gate: 4,000 offers must compute in < 5 seconds."""
        import time

        OFFER_COUNT = 4_000
        THRESHOLD_SECONDS = 5.0

        # Build synthetic tasks with stories (cache-hit path)
        tasks = []
        stories_by_gid: dict[str, list[dict]] = {}

        for i in range(OFFER_COUNT):
            task = _make_task_mock(
                gid=f"task_{i}",
                created_at="2025-01-01T00:00:00.000Z",
                section_name="ACTIVE",
                office_phone=f"+1206555{i:04d}",
                offer_id=f"OFR-{i:04d}",
            )
            tasks.append(task)

            # Each task has 2 section_changed stories (typical case)
            stories_by_gid[f"task_{i}"] = [
                {
                    "gid": f"s_{i}_1",
                    "resource_subtype": "section_changed",
                    "created_at": "2025-01-02T00:00:00.000Z",
                    "new_section": {"gid": "sec1", "name": "ACTIVATING"},
                    "old_section": {"gid": "sec0", "name": "Sales Process"},
                },
                {
                    "gid": f"s_{i}_2",
                    "resource_subtype": "section_changed",
                    "created_at": "2025-01-10T00:00:00.000Z",
                    "new_section": {"gid": "sec2", "name": "ACTIVE"},
                    "old_section": {"gid": "sec1", "name": "ACTIVATING"},
                },
            ]

        # Mock the client and cache provider
        client = MagicMock()
        client._cache_provider = MagicMock()

        # Mock task enumeration
        task_result = MagicMock()
        task_result.collect = AsyncMock(return_value=tasks)
        client.tasks.list_async = MagicMock(return_value=task_result)

        # Patch derived cache (miss) and story cache (all hits)
        with (
            patch(
                "autom8_asana.cache.integration.derived.get_cached_timelines",
                return_value=None,
            ),
            patch(
                "autom8_asana.cache.integration.stories.read_stories_batch",
                return_value=stories_by_gid,
            ),
            patch(
                "autom8_asana.cache.integration.derived.store_derived_timelines",
            ),
        ):
            start = time.perf_counter()
            entries = await get_or_compute_timelines(
                client=client,
                project_gid="proj_123",
                classifier_name="offer",
                period_start=date(2025, 1, 1),
                period_end=date(2025, 3, 31),
            )
            elapsed = time.perf_counter() - start

        assert len(entries) == OFFER_COUNT, f"Expected {OFFER_COUNT} entries, got {len(entries)}"
        assert elapsed < THRESHOLD_SECONDS, (
            f"SCAR-015 regression: {OFFER_COUNT} offers took {elapsed:.2f}s "
            f"(threshold: {THRESHOLD_SECONDS}s)"
        )
