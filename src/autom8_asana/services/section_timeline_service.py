"""Section timeline service for reconstructing offer section histories.

Per TDD-SECTION-TIMELINE-001: Orchestrates story fetching, filtering,
timeline construction, and day counting for all offers in the Business
Offers project.

Architecture (DEF-006 fix): All I/O (task enumeration + story fetching)
happens at warm-up time via build_all_timelines(). The pre-computed
SectionTimeline objects are stored on app.state.offer_timelines.
At request time, compute_timeline_entries() reads from this pre-computed
cache and performs pure-CPU day counting — no I/O, no API calls.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from autom8y_log import get_logger

from autom8_asana.client import AsanaClient
from autom8_asana.models.business.activity import (
    OFFER_CLASSIFIER,
    AccountActivity,
    extract_section_name,
)
from autom8_asana.models.business.section_timeline import (
    OfferTimelineEntry,
    SectionInterval,
    SectionTimeline,
)
from autom8_asana.models.story import Story

logger = get_logger(__name__)

# Bounded concurrency for S3-backed warm-up (per SPIKE-SECTION-TIMELINE-CACHE).
# Production has ~3,800 offers. Semaphore(5) avoids Asana API rate limits while
# still parallelizing S3 → Redis promotions (safe to parallelize).
# Reduced from 20 after production confirmed 291 rate_limit_429 events at
# Semaphore(20) with 3,771 offers (DEF-004 postmortem 2026-02-19).
_WARM_CONCURRENCY = 5

# Bounded concurrency for timeline building during warm-up.
# After story caches are warm, building timelines is fast (cache hits only).
_BUILD_CONCURRENCY = 20

# Wall-clock timeout for the pre-warm task. Sized for ~3,800 offers at
# Semaphore(5): ~760 batches × ~100ms S3 promotion = ~76s (S3-warm path);
# API-cold path is slower but tolerated up to 30 minutes on first-ever deploy.
# Increased from 600s after production confirmed timeout at 3,771 offers.
_WARM_TIMEOUT_SECONDS = 1800  # 30 minutes

# Business Offers project GID (matches Offer.PRIMARY_PROJECT_GID)
BUSINESS_OFFERS_PROJECT_GID = "1143843662099250"

# Story opt_fields for section_changed extraction
_STORY_OPT_FIELDS: list[str] = [
    "gid",
    "resource_subtype",
    "created_at",
    "new_section.name",
    "old_section.name",
]

# Task opt_fields for offer enumeration
_TASK_OPT_FIELDS: list[str] = [
    "gid",
    "created_at",
    "memberships.section.name",
    "memberships.project.gid",
    "custom_fields.name",
    "custom_fields.text_value",
]


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO 8601 datetime string to datetime.

    Handles Asana's format: "2024-01-15T10:30:00.000Z"

    Args:
        value: ISO 8601 datetime string or None.

    Returns:
        Parsed datetime or None.
    """
    if value is None:
        return None
    # Strip trailing 'Z' and parse
    clean = value.replace("Z", "+00:00")
    return datetime.fromisoformat(clean)


def _is_cross_project_noise(story: Story) -> bool:
    """Check if a section_changed story is cross-project noise.

    Per AC-1.3: If BOTH old_section and new_section classify as None,
    this story is from a non-Business-Offers project and should be
    skipped.

    Per AC-1.4: If only one side is None, the story is retained.

    Args:
        story: Story with resource_subtype == "section_changed".

    Returns:
        True if the story should be filtered out (both sides unknown).
    """
    new_name = story.new_section.name if story.new_section else None
    old_name = story.old_section.name if story.old_section else None

    new_cls = OFFER_CLASSIFIER.classify(new_name) if new_name else None
    old_cls = OFFER_CLASSIFIER.classify(old_name) if old_name else None

    return new_cls is None and old_cls is None


def _extract_office_phone(task_data: dict[str, Any]) -> str | None:
    """Extract office_phone custom field from raw task data.

    Walks custom_fields array looking for the "Office Phone" field.

    Args:
        task_data: Raw task dict from Asana API.

    Returns:
        Office phone string or None.
    """
    custom_fields = task_data.get("custom_fields") or []
    for cf in custom_fields:
        if isinstance(cf, dict) and cf.get("name") == "Office Phone":
            return cf.get("text_value")
    return None


def _build_intervals_from_stories(
    stories: list[Story],
    offer_gid: str | None = None,
) -> tuple[list[SectionInterval], int]:
    """Walk filtered stories chronologically to produce SectionInterval list.

    Per AC-2.5: Each story closes the previous interval and opens a new one.
    Per AC-2.6: The final interval has exited_at=None.
    Per AC-2.3: Unknown sections get classification=None + WARNING log including
        offer_gid for correlation.

    Args:
        stories: Section-changed stories, already filtered, sorted by
            created_at ascending.
        offer_gid: Task GID of the offer (for WARNING log correlation per AC-2.3).

    Returns:
        Tuple of (intervals list, story count used).
    """
    if not stories:
        return [], 0

    intervals: list[SectionInterval] = []
    story_count = len(stories)

    for story in stories:
        section_name = (
            story.new_section.name if story.new_section else None
        ) or "UNKNOWN"
        classification = OFFER_CLASSIFIER.classify(section_name)

        if classification is None:
            logger.warning(
                "unknown_section_in_timeline",
                extra={
                    "section_name": section_name,
                    "story_gid": story.gid,
                    "offer_gid": offer_gid,
                },
            )

        entered_at = _parse_datetime(story.created_at)
        if entered_at is None:
            continue

        # Close previous interval
        if intervals:
            prev = intervals[-1]
            intervals[-1] = SectionInterval(
                section_name=prev.section_name,
                classification=prev.classification,
                entered_at=prev.entered_at,
                exited_at=entered_at,
            )

        # Open new interval (AC-2.6: last one stays open)
        intervals.append(
            SectionInterval(
                section_name=section_name,
                classification=classification,
                entered_at=entered_at,
                exited_at=None,
            )
        )

    return intervals, story_count


def _build_imputed_interval(
    task_created_at: datetime | None,
    account_activity: AccountActivity | None,
    section_name: str,
) -> list[SectionInterval]:
    """Build a single imputed interval for a never-moved task.

    Per AC-3.1: If zero stories remain, impute [task.created_at, None].
    Per AC-3.2: Use the offer's current account_activity for classification.

    Args:
        task_created_at: Task creation timestamp.
        account_activity: Current section classification.
        section_name: Current section name.

    Returns:
        List containing one SectionInterval, or empty if no created_at.
    """
    if task_created_at is None:
        return []

    return [
        SectionInterval(
            section_name=section_name,
            classification=account_activity,
            entered_at=task_created_at,
            exited_at=None,
        )
    ]


async def build_timeline_for_offer(
    client: AsanaClient,
    offer_gid: str,
    office_phone: str | None,
    task_created_at: datetime | None,
    current_section_name: str | None,
    current_account_activity: AccountActivity | None,
) -> SectionTimeline:
    """Build a SectionTimeline for a single offer.

    Per FR-1: Fetch and filter stories.
    Per FR-2: Walk chronologically to produce intervals.
    Per FR-3: Handle never-moved tasks via imputation.

    Args:
        client: AsanaClient for story fetching.
        offer_gid: Offer task GID.
        office_phone: Office phone custom field value.
        task_created_at: Task creation timestamp.
        current_section_name: Current section name (for imputation).
        current_account_activity: Current classification (for imputation).

    Returns:
        SectionTimeline for this offer.
    """
    # FR-1: Fetch stories via cached client.
    # max_cache_age_seconds=7200: If the story cache was populated during
    # warm-up (runs every ~12 min on ECS restart), skip the Asana API
    # refresh entirely.  Stories fetched within the last 2 hours are current
    # enough for historical day-counting.
    stories = await client.stories.list_for_task_cached_async(  # type: ignore[attr-defined]  # generated by @async_method
        offer_gid,
        opt_fields=_STORY_OPT_FIELDS,
        max_cache_age_seconds=7200,
    )

    # AC-1.2: Filter to section_changed only
    section_stories = [s for s in stories if s.resource_subtype == "section_changed"]

    # AC-1.3, AC-1.4: Filter cross-project noise
    filtered_stories = [s for s in section_stories if not _is_cross_project_noise(s)]

    # Sort by created_at ascending (AC-2.5)
    filtered_stories.sort(key=lambda s: s.created_at or "")

    # FR-2: Build intervals from filtered stories
    intervals, story_count = _build_intervals_from_stories(
        filtered_stories, offer_gid=offer_gid
    )

    # FR-3: Handle never-moved task
    if not intervals:
        intervals = _build_imputed_interval(
            task_created_at,
            current_account_activity,
            current_section_name or "UNKNOWN",
        )
        story_count = 0

    return SectionTimeline(
        offer_gid=offer_gid,
        office_phone=office_phone,
        intervals=tuple(intervals),
        task_created_at=task_created_at,
        story_count=story_count,
    )


def compute_timeline_entries(
    offer_timelines: list[tuple[str, str | None, SectionTimeline]],
    period_start: date,
    period_end: date,
) -> list[OfferTimelineEntry]:
    """Compute day-count entries from pre-built timelines. Pure CPU, no I/O.

    Per DEF-006 fix: All I/O (task enumeration, story fetching) is done at
    warm-up time by build_all_timelines(). This function is called at request
    time and only does set-based day counting — ~3,800 offers complete in <100ms.

    Args:
        offer_timelines: Pre-computed (offer_gid, office_phone, SectionTimeline)
            tuples from build_all_timelines(), stored on app.state.
        period_start: Query period start (inclusive).
        period_end: Query period end (inclusive).

    Returns:
        List of OfferTimelineEntry with day counts for the requested period.
    """
    entries: list[OfferTimelineEntry] = []
    for offer_gid, office_phone, timeline in offer_timelines:
        active_days = timeline.active_days_in_period(period_start, period_end)
        billable_days = timeline.billable_days_in_period(period_start, period_end)
        entries.append(
            OfferTimelineEntry(
                offer_gid=offer_gid,
                office_phone=office_phone,
                active_section_days=active_days,
                billable_section_days=billable_days,
            )
        )
    return entries


async def build_all_timelines(
    client: AsanaClient,
    on_progress: Callable[[int, int], Any] | None = None,
) -> list[tuple[str, str | None, SectionTimeline]]:
    """Enumerate all offers and build SectionTimeline for each. Run at warm-up.

    Per DEF-006 fix: Moves ALL I/O to warm-up time. Enumerates tasks from the
    Asana API, then builds a SectionTimeline for each offer using cached stories.
    The result is stored on app.state.offer_timelines and served at request time
    via compute_timeline_entries() (pure CPU).

    Args:
        client: AsanaClient for Asana API calls (with shared cache_provider).
        on_progress: Optional callback(built, total) for progress tracking.

    Returns:
        List of (offer_gid, office_phone, SectionTimeline) tuples.
    """
    # Enumerate all tasks in Business Offers project
    tasks = await client.tasks.list_async(
        project=BUSINESS_OFFERS_PROJECT_GID,
        opt_fields=_TASK_OPT_FIELDS,
    ).collect()

    total = len(tasks)
    sem = asyncio.Semaphore(_BUILD_CONCURRENCY)
    built_count = 0

    logger.info(
        "timeline_build_started",
        extra={"total_offers": total, "concurrency": _BUILD_CONCURRENCY},
    )

    async def _build_one(
        task: Any,
    ) -> tuple[str, str | None, SectionTimeline] | None:
        nonlocal built_count
        async with sem:
            try:
                task_created_at = _parse_datetime(task.created_at)
                section_name = extract_section_name(
                    task, project_gid=BUSINESS_OFFERS_PROJECT_GID
                )
                account_activity = (
                    OFFER_CLASSIFIER.classify(section_name) if section_name else None
                )
                office_phone = _extract_office_phone(task.model_dump())

                timeline = await build_timeline_for_offer(
                    client=client,
                    offer_gid=task.gid,
                    office_phone=office_phone,
                    task_created_at=task_created_at,
                    current_section_name=section_name,
                    current_account_activity=account_activity,
                )

                built_count += 1
                if on_progress is not None:
                    on_progress(built_count, total)

                return (task.gid, office_phone, timeline)
            except Exception:
                logger.warning(
                    "timeline_build_offer_failed",
                    extra={"offer_gid": task.gid},
                    exc_info=True,
                )
                return None

    results = await asyncio.gather(
        *[_build_one(task) for task in tasks],
        return_exceptions=True,
    )

    timelines = [r for r in results if isinstance(r, tuple)]

    logger.info(
        "timeline_build_complete",
        extra={"total_offers": total, "built": len(timelines)},
    )

    return timelines


async def warm_story_caches(
    client: AsanaClient,
    on_progress: Callable[..., Any] | None = None,
) -> tuple[int, int]:
    """Pre-warm story caches for all offers in the Business Offers project.

    Per FR-7/AC-7.2: Iterates over all offers and calls
    list_for_task_cached() to populate the incremental story cache.

    Per AC-7.6: Individual failures are logged at WARNING and do not
    abort the overall warm-up.

    Per SPIKE-SECTION-TIMELINE-CACHE: Uses bounded-parallel concurrency
    (_WARM_CONCURRENCY) instead of sequential iteration. S3 -> Redis promotion
    is I/O-safe to parallelize; only Asana API fetches need rate-limit care,
    and list_for_task_cached() handles that internally (writes to S3 are
    sequential within each offer's cache path).

    Args:
        client: AsanaClient for Asana API calls.
        on_progress: Optional callback(warmed: int, total: int) for
            progress tracking.

    Returns:
        Tuple of (warmed_count, total_count).
    """
    # Enumerate all offers
    tasks = await client.tasks.list_async(
        project=BUSINESS_OFFERS_PROJECT_GID,
        opt_fields=["gid"],
    ).collect()

    total = len(tasks)
    sem = asyncio.Semaphore(_WARM_CONCURRENCY)

    logger.info(
        "story_cache_warm_started",
        extra={"total_offers": total, "concurrency": _WARM_CONCURRENCY},
    )

    # DEF-008 fix: track progress incrementally via shared counter so the
    # 50% readiness gate (AC-7.4) can fire mid-warm-up, not only at 100%.
    warmed_count = 0

    async def _warm_one(gid: str) -> bool:
        """Warm a single offer's story cache. Returns True on success."""
        nonlocal warmed_count
        async with sem:
            try:
                await client.stories.list_for_task_cached_async(  # type: ignore[attr-defined]  # generated by @async_method
                    gid,
                    opt_fields=_STORY_OPT_FIELDS,
                )
                warmed_count += 1
                if on_progress is not None:
                    on_progress(warmed_count, total)
                return True
            except Exception:
                logger.warning(
                    "story_cache_warm_offer_failed",
                    extra={"offer_gid": gid},
                    exc_info=True,
                )
                return False

    # Run bounded-parallel warm; gather results to track progress.
    # Return_exceptions=True ensures one failure doesn't cancel others.
    results = await asyncio.gather(
        *[_warm_one(task.gid) for task in tasks],
        return_exceptions=True,
    )

    warmed = sum(1 for r in results if r is True)

    logger.info(
        "story_cache_warm_complete",
        extra={"warmed": warmed, "total": total},
    )

    return warmed, total
