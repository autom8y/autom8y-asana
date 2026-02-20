"""Tests for get_or_compute_timelines service function.

Per TDD-SECTION-TIMELINE-REMEDIATION: Tests for the compute-on-read-then-cache
orchestration:
- Cache hit path (derived cache returns data, no task enumeration)
- Cache miss path (lock, enumerate, batch-read, build, store)
- Lock re-check path (concurrent request finds cache after lock)
- Unknown classifier name returns empty list
- No cache provider returns empty list
- Cache store failure still returns computed results
- Generic parameterization (offer vs unit classifier)
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.cache.models.entry import (
    CacheEntry,
    DerivedTimelineCacheEntry,
    EntryType,
)
from autom8_asana.models.business.activity import AccountActivity
from autom8_asana.models.business.section_timeline import (
    OfferTimelineEntry,
    SectionInterval,
    SectionTimeline,
)
from autom8_asana.services.section_timeline_service import (
    _computation_locks,
    get_or_compute_timelines,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=UTC)


def _make_serialized_timeline(
    offer_gid: str = "offer1",
    office_phone: str | None = "555-0100",
    entered_at: str = "2025-01-01T00:00:00+00:00",
    exited_at: str | None = None,
    section_name: str = "ACTIVE",
    classification: str | None = "active",
    task_created_at: str | None = "2024-12-01T00:00:00+00:00",
    story_count: int = 1,
) -> dict[str, Any]:
    """Build a serialized timeline dict as stored in derived cache."""
    return {
        "offer_gid": offer_gid,
        "office_phone": office_phone,
        "intervals": [
            {
                "section_name": section_name,
                "classification": classification,
                "entered_at": entered_at,
                "exited_at": exited_at,
            }
        ],
        "task_created_at": task_created_at,
        "story_count": story_count,
    }


def _make_derived_entry(
    project_gid: str = "proj1",
    classifier_name: str = "offer",
    timelines_data: list[dict[str, Any]] | None = None,
) -> DerivedTimelineCacheEntry:
    """Build a DerivedTimelineCacheEntry for testing."""
    if timelines_data is None:
        timelines_data = [_make_serialized_timeline()]
    now = datetime.now(UTC)
    key = f"timeline:{project_gid}:{classifier_name}"
    return DerivedTimelineCacheEntry(
        key=key,
        data={"timelines": timelines_data},
        entry_type=EntryType.DERIVED_TIMELINE,
        version=now,
        cached_at=now,
        ttl=300,
        project_gid=project_gid,
        metadata={"computed_at": now.isoformat()},
        classifier_name=classifier_name,
        source_entity_count=1,
        source_cache_hits=1,
        source_cache_misses=0,
        computation_duration_ms=100.0,
    )


def _make_task_mock(
    gid: str,
    created_at: str = "2025-01-01T00:00:00.000Z",
    section_name: str | None = "ACTIVE",
    project_gid: str = "proj1",
    office_phone: str | None = None,
) -> MagicMock:
    """Build a mock Task object."""
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


def _make_client_with_cache(
    cache_provider: Any | None = None,
    tasks: list[Any] | None = None,
) -> MagicMock:
    """Build a mock AsanaClient with _cache_provider and tasks.list_async."""
    client = MagicMock()
    client._cache_provider = cache_provider

    # Mock tasks.list_async().collect() chain
    collector = AsyncMock(return_value=tasks or [])
    list_result = MagicMock()
    list_result.collect = collector
    client.tasks.list_async = MagicMock(return_value=list_result)

    return client


# Patch targets: get_cached_timelines, store_derived_timelines, and
# read_stories_batch are imported locally inside get_or_compute_timelines().
# We must patch them at their source modules.
_PATCH_GET_CACHED = "autom8_asana.cache.integration.derived.get_cached_timelines"
_PATCH_STORE = "autom8_asana.cache.integration.derived.store_derived_timelines"
_PATCH_BATCH = "autom8_asana.cache.integration.stories.read_stories_batch"


@pytest.fixture(autouse=True)
def _clear_computation_locks():
    """Clear computation locks between tests to prevent leakage."""
    _computation_locks.clear()
    yield
    _computation_locks.clear()


# ---------------------------------------------------------------------------
# Cache Hit Path
# ---------------------------------------------------------------------------


class TestCacheHitPath:
    @pytest.mark.asyncio
    async def test_returns_entries_from_cached_timelines(self) -> None:
        """Derived cache hit: returns OfferTimelineEntry list without enumeration."""
        derived_entry = _make_derived_entry()

        with patch(
            _PATCH_GET_CACHED,
            return_value=derived_entry,
        ), patch(
            _PATCH_BATCH,
        ) as mock_batch:
            client = _make_client_with_cache(cache_provider=MagicMock())

            result = await get_or_compute_timelines(
                client=client,
                project_gid="proj1",
                classifier_name="offer",
                period_start=date(2025, 1, 1),
                period_end=date(2025, 1, 31),
            )

            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], OfferTimelineEntry)
            assert result[0].offer_gid == "offer1"

            # Should NOT call batch read or task enumeration
            mock_batch.assert_not_called()
            client.tasks.list_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_hit_computes_day_counts(self) -> None:
        """Cached timelines are used to compute day counts for the period."""
        # Build a timeline where ACTIVE interval covers entire January
        timeline_data = _make_serialized_timeline(
            entered_at="2025-01-01T00:00:00+00:00",
            exited_at=None,
            classification="active",
        )
        derived_entry = _make_derived_entry(timelines_data=[timeline_data])

        with patch(
            _PATCH_GET_CACHED,
            return_value=derived_entry,
        ):
            client = _make_client_with_cache(cache_provider=MagicMock())

            result = await get_or_compute_timelines(
                client=client,
                project_gid="proj1",
                classifier_name="offer",
                period_start=date(2025, 1, 1),
                period_end=date(2025, 1, 31),
            )

            assert result[0].active_section_days == 31
            assert result[0].billable_section_days == 31


# ---------------------------------------------------------------------------
# Cache Miss Path
# ---------------------------------------------------------------------------


class TestCacheMissPath:
    @pytest.mark.asyncio
    async def test_enumerates_tasks_on_miss(self) -> None:
        """Cache miss: enumerates tasks, reads stories, builds timelines."""
        task = _make_task_mock(
            "t1", section_name="ACTIVE", project_gid="proj1"
        )
        cache = MagicMock()
        cache.get_versioned.return_value = None
        cache.set_versioned.return_value = None

        stories_batch = {
            "t1": [
                {
                    "gid": "s1",
                    "resource_subtype": "section_changed",
                    "created_at": "2025-01-01T00:00:00.000Z",
                    "new_section": {"gid": "sec1", "name": "ACTIVE"},
                    "old_section": {"gid": "sec2", "name": "ACTIVATING"},
                }
            ]
        }

        with patch(
            _PATCH_GET_CACHED,
            return_value=None,
        ), patch(
            _PATCH_BATCH,
            return_value=stories_batch,
        ), patch(
            _PATCH_STORE,
        ) as mock_store:
            client = _make_client_with_cache(
                cache_provider=cache, tasks=[task]
            )

            result = await get_or_compute_timelines(
                client=client,
                project_gid="proj1",
                classifier_name="offer",
                period_start=date(2025, 1, 1),
                period_end=date(2025, 1, 31),
            )

            # Should enumerate tasks
            client.tasks.list_async.assert_called_once()

            # Should store derived entry
            mock_store.assert_called_once()

            assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_cache_miss_with_no_stories_imputes(self) -> None:
        """EC-6: Entity with no cached stories imputes from task data."""
        task = _make_task_mock(
            "t1",
            created_at="2025-01-01T00:00:00.000Z",
            section_name="ACTIVE",
            project_gid="proj1",
        )
        cache = MagicMock()
        cache.get_versioned.return_value = None
        cache.set_versioned.return_value = None

        # All stories are cache misses
        stories_batch = {"t1": None}

        with patch(
            _PATCH_GET_CACHED,
            return_value=None,
        ), patch(
            _PATCH_BATCH,
            return_value=stories_batch,
        ), patch(
            _PATCH_STORE,
        ):
            client = _make_client_with_cache(
                cache_provider=cache, tasks=[task]
            )

            result = await get_or_compute_timelines(
                client=client,
                project_gid="proj1",
                classifier_name="offer",
                period_start=date(2025, 1, 1),
                period_end=date(2025, 1, 31),
            )

            # Should still produce a result via imputation
            assert len(result) == 1
            assert result[0].offer_gid == "t1"


# ---------------------------------------------------------------------------
# Lock Re-check Path (concurrent request)
# ---------------------------------------------------------------------------


class TestLockRecheck:
    @pytest.mark.asyncio
    async def test_second_request_finds_cache_after_lock(self) -> None:
        """EC-3: Concurrent request waits for lock, then finds cache."""
        derived_entry = _make_derived_entry()

        call_count = 0

        def side_effect_get_cached(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            # First call (before lock): miss. Second call (after lock): hit.
            if call_count <= 1:
                return None
            return derived_entry

        task = _make_task_mock("t1", section_name="ACTIVE", project_gid="proj1")
        cache = MagicMock()
        cache.get_versioned.return_value = None
        cache.set_versioned.return_value = None

        with patch(
            _PATCH_GET_CACHED,
            side_effect=side_effect_get_cached,
        ), patch(
            _PATCH_BATCH,
            return_value={},
        ), patch(
            _PATCH_STORE,
        ) as mock_store:
            client = _make_client_with_cache(
                cache_provider=cache, tasks=[task]
            )

            result = await get_or_compute_timelines(
                client=client,
                project_gid="proj1",
                classifier_name="offer",
                period_start=date(2025, 1, 1),
                period_end=date(2025, 1, 31),
            )

            # Second call found cache, so should not store
            mock_store.assert_not_called()
            assert len(result) >= 1


# ---------------------------------------------------------------------------
# Error/Edge Cases
# ---------------------------------------------------------------------------


class TestErrorCases:
    @pytest.mark.asyncio
    async def test_unknown_classifier_returns_empty(self) -> None:
        """Unknown classifier_name returns empty list."""
        client = _make_client_with_cache(cache_provider=MagicMock())

        result = await get_or_compute_timelines(
            client=client,
            project_gid="proj1",
            classifier_name="nonexistent_classifier",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_no_cache_provider_returns_empty(self) -> None:
        """Client without _cache_provider returns empty list."""
        client = _make_client_with_cache(cache_provider=None)

        result = await get_or_compute_timelines(
            client=client,
            project_gid="proj1",
            classifier_name="offer",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_cache_store_failure_still_returns_results(self) -> None:
        """Per TDD Section 8.2: Store failure returns computed results."""
        task = _make_task_mock(
            "t1",
            created_at="2025-01-01T00:00:00.000Z",
            section_name="ACTIVE",
            project_gid="proj1",
        )
        cache = MagicMock()
        cache.get_versioned.return_value = None
        cache.set_versioned.return_value = None

        stories_batch = {"t1": None}

        with patch(
            _PATCH_GET_CACHED,
            return_value=None,
        ), patch(
            _PATCH_BATCH,
            return_value=stories_batch,
        ), patch(
            _PATCH_STORE,
            side_effect=RuntimeError("Redis connection failed"),
        ):
            client = _make_client_with_cache(
                cache_provider=cache, tasks=[task]
            )

            # Should not raise -- store failure is logged, results still returned
            result = await get_or_compute_timelines(
                client=client,
                project_gid="proj1",
                classifier_name="offer",
                period_start=date(2025, 1, 1),
                period_end=date(2025, 1, 31),
            )

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_task_enumeration_failure_raises(self) -> None:
        """Task enumeration failure propagates as exception."""
        cache = MagicMock()
        cache.get_versioned.return_value = None

        with patch(
            _PATCH_GET_CACHED,
            return_value=None,
        ):
            client = MagicMock()
            client._cache_provider = cache
            # Make task enumeration fail
            collector = AsyncMock(side_effect=RuntimeError("Asana API error"))
            list_result = MagicMock()
            list_result.collect = collector
            client.tasks.list_async = MagicMock(return_value=list_result)

            with pytest.raises(RuntimeError, match="Asana API error"):
                await get_or_compute_timelines(
                    client=client,
                    project_gid="proj1",
                    classifier_name="offer",
                    period_start=date(2025, 1, 1),
                    period_end=date(2025, 1, 31),
                )


# ---------------------------------------------------------------------------
# Generic Parameterization (offer vs unit)
# ---------------------------------------------------------------------------


class TestGenericParameterization:
    @pytest.mark.asyncio
    async def test_offer_classifier(self) -> None:
        """offer classifier resolves and works."""
        derived_entry = _make_derived_entry(classifier_name="offer")

        with patch(
            _PATCH_GET_CACHED,
            return_value=derived_entry,
        ):
            client = _make_client_with_cache(cache_provider=MagicMock())

            result = await get_or_compute_timelines(
                client=client,
                project_gid="proj1",
                classifier_name="offer",
                period_start=date(2025, 1, 1),
                period_end=date(2025, 1, 31),
            )

            assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_unit_classifier(self) -> None:
        """unit classifier resolves and works (SC-3)."""
        derived_entry = _make_derived_entry(classifier_name="unit")

        with patch(
            _PATCH_GET_CACHED,
            return_value=derived_entry,
        ):
            client = _make_client_with_cache(cache_provider=MagicMock())

            result = await get_or_compute_timelines(
                client=client,
                project_gid="proj1",
                classifier_name="unit",
                period_start=date(2025, 1, 1),
                period_end=date(2025, 1, 31),
            )

            assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_different_classifiers_use_different_cache_keys(
        self,
    ) -> None:
        """Offer and unit use different derived cache keys."""
        offer_entry = _make_derived_entry(classifier_name="offer")
        unit_entry = _make_derived_entry(classifier_name="unit")

        assert offer_entry.key != unit_entry.key
