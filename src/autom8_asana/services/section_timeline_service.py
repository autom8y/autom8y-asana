"""Section timeline service for reconstructing offer section histories.

Per TDD-SECTION-TIMELINE-001: Orchestrates story fetching, filtering,
timeline construction, and day counting for all offers in the Business
Offers project.

Per TDD-SECTION-TIMELINE-REMEDIATION: Adds compute-on-read-then-cache
architecture via get_or_compute_timelines(). Timeline data is computed on
first request from cached stories, stored as a derived cache entry, and
served from cache on subsequent requests. No warm-up pipeline required.
"""

from __future__ import annotations

import asyncio
import time as time_module
from collections import defaultdict
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.client import AsanaClient
from autom8_asana.models.business.activity import (
    CLASSIFIERS,
    OFFER_CLASSIFIER,
    AccountActivity,
    SectionClassifier,
    extract_section_name,
)
from autom8_asana.models.business.section_timeline import (
    OfferTimelineEntry,
    SectionInterval,
    SectionTimeline,
)
from autom8_asana.models.story import Story

if TYPE_CHECKING:
    from autom8_asana.protocols.cache import CacheProvider

logger = get_logger(__name__)

# --- Computation lock for thundering-herd prevention (AMB-3) ---
# Per TDD-SECTION-TIMELINE-REMEDIATION: In-process asyncio.Lock keyed
# by (project_gid, classifier_name) prevents concurrent computation
# of the same derived entry.
_computation_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


def _get_computation_lock(project_gid: str, classifier_name: str) -> asyncio.Lock:
    """Get or create a computation lock for a (project, classifier) pair.

    Args:
        project_gid: Asana project GID.
        classifier_name: Classifier name.

    Returns:
        asyncio.Lock for this (project, classifier) pair.
    """
    key = f"{project_gid}:{classifier_name}"
    return _computation_locks[key]


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


def _is_cross_project_noise(
    story: Story,
    classifier: SectionClassifier | None = None,
) -> bool:
    """Check if a section_changed story is cross-project noise.

    Per AC-1.3: If BOTH old_section and new_section classify as None,
    this story is from a non-Business-Offers project and should be
    skipped.

    Per AC-1.4: If only one side is None, the story is retained.

    Per TDD-SECTION-TIMELINE-REMEDIATION Section 7.3: Accepts a
    classifier parameter for generic entity parameterization.

    Args:
        story: Story with resource_subtype == "section_changed".
        classifier: SectionClassifier to use. Defaults to OFFER_CLASSIFIER
            for backward compatibility.

    Returns:
        True if the story should be filtered out (both sides unknown).
    """
    if classifier is None:
        classifier = OFFER_CLASSIFIER

    new_name = story.new_section.name if story.new_section else None
    old_name = story.old_section.name if story.old_section else None

    new_cls = classifier.classify(new_name) if new_name else None
    old_cls = classifier.classify(old_name) if old_name else None

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
    classifier: SectionClassifier | None = None,
    entity_gid: str | None = None,
) -> tuple[list[SectionInterval], int]:
    """Walk filtered stories chronologically to produce SectionInterval list.

    Per AC-2.5: Each story closes the previous interval and opens a new one.
    Per AC-2.6: The final interval has exited_at=None.
    Per AC-2.3: Unknown sections get classification=None + WARNING log including
        entity_gid for correlation.

    Per TDD-SECTION-TIMELINE-REMEDIATION Section 7.3: Accepts a
    classifier parameter for generic entity parameterization.

    Args:
        stories: Section-changed stories, already filtered, sorted by
            created_at ascending.
        classifier: SectionClassifier to use. Defaults to OFFER_CLASSIFIER
            for backward compatibility.
        entity_gid: Task GID of the entity (for WARNING log correlation per AC-2.3).

    Returns:
        Tuple of (intervals list, story count used).
    """
    if classifier is None:
        classifier = OFFER_CLASSIFIER

    if not stories:
        return [], 0

    intervals: list[SectionInterval] = []
    story_count = len(stories)

    for story in stories:
        section_name = (
            story.new_section.name if story.new_section else None
        ) or "UNKNOWN"
        classification = classifier.classify(section_name)

        if classification is None:
            logger.warning(
                "unknown_section_in_timeline",
                extra={
                    "section_name": section_name,
                    "story_gid": story.gid,
                    "offer_gid": entity_gid,
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

    Fetch and filter stories.
    Walk chronologically to produce intervals.
    Handle never-moved tasks via imputation.

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
    # Fetch stories via cached client.
    # max_cache_age_seconds=7200: Stories cached within the last 2 hours are
    # current enough for historical day-counting. Skips the Asana API refresh
    # for recently-cached entries.
    stories = await client.stories.list_for_task_cached_async(  # type: ignore[attr-defined]  # generated by @async_method
        offer_gid,
        opt_fields=_STORY_OPT_FIELDS,
        max_cache_age_seconds=7200,
    )

    # Filter to section_changed only
    section_stories = [s for s in stories if s.resource_subtype == "section_changed"]

    # Filter cross-project noise
    filtered_stories = [
        s for s in section_stories if not _is_cross_project_noise(s, OFFER_CLASSIFIER)
    ]

    # Sort by created_at ascending
    filtered_stories.sort(key=lambda s: s.created_at or "")

    # Build intervals from filtered stories
    intervals, story_count = _build_intervals_from_stories(
        filtered_stories, classifier=OFFER_CLASSIFIER, entity_gid=offer_gid
    )

    # Handle never-moved task
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


async def get_or_compute_timelines(
    client: AsanaClient,
    project_gid: str,
    classifier_name: str,
    period_start: date,
    period_end: date,
    classification_filter: str | None = None,
) -> list[OfferTimelineEntry]:
    """Get timeline entries, computing from cache if needed.

    Per TDD-SECTION-TIMELINE-REMEDIATION Section 5.2: Implements
    compute-on-read-then-cache architecture:

    1. Check derived cache for pre-computed timelines.
    2. If cache miss, acquire computation lock and re-check.
    3. Enumerate tasks via Asana API.
    4. Batch-read cached stories (pure-read, no API calls).
    5. Build timelines from cached stories.
    6. Store computed result in derived cache.
    7. Compute day counts for the requested period.

    Uses asyncio.Lock per (project_gid, classifier_name) to prevent
    thundering herd on cold cache (AMB-3).

    Classification filtering is applied post-cache as O(n) filtering --
    the derived cache always stores all timelines regardless of filter.

    Args:
        client: AsanaClient (for task enumeration on cache miss).
        project_gid: Asana project GID.
        classifier_name: Classifier name ("offer", "unit").
        period_start: Query period start (inclusive).
        period_end: Query period end (inclusive).
        classification_filter: If provided, only include entries whose
            current_classification matches this value (e.g., "active").

    Returns:
        List of OfferTimelineEntry with day counts.
    """
    from autom8_asana.cache.integration.derived import (
        _deserialize_timeline,
        _serialize_timeline,
        get_cached_timelines,
        store_derived_timelines,
    )
    from autom8_asana.cache.integration.stories import read_stories_batch

    # Resolve classifier from registry
    classifier = CLASSIFIERS.get(classifier_name)
    if classifier is None:
        logger.error(
            "unknown_classifier_name",
            extra={"classifier_name": classifier_name},
        )
        return []

    # Resolve cache provider from the client.
    # AsanaClient stores its provider as _cache_provider (private).
    # _PooledClientWrapper proxies attribute access via __getattr__.
    cache: CacheProvider | None = getattr(client, "_cache_provider", None)
    if cache is None:
        logger.warning(
            "timeline_no_cache_provider",
            extra={
                "project_gid": project_gid,
                "classifier_name": classifier_name,
            },
        )
        return []

    # Step 1: Check derived cache for pre-computed timelines
    cached_entry = get_cached_timelines(project_gid, classifier_name, cache)
    if cached_entry is not None:
        timelines_data = cached_entry.data.get("timelines", [])
        timelines = [_deserialize_timeline(d) for d in timelines_data]
        return _compute_day_counts(
            timelines,
            period_start,
            period_end,
            classifier=classifier,
            classification_filter=classification_filter,
        )

    # Step 2: Acquire computation lock (AMB-3: thundering herd prevention)
    lock = _get_computation_lock(project_gid, classifier_name)
    async with lock:
        # Re-check cache after acquiring lock (another request may have computed)
        cached_entry = get_cached_timelines(project_gid, classifier_name, cache)
        if cached_entry is not None:
            timelines_data = cached_entry.data.get("timelines", [])
            timelines = [_deserialize_timeline(d) for d in timelines_data]
            return _compute_day_counts(
                timelines,
                period_start,
                period_end,
                classifier=classifier,
                classification_filter=classification_filter,
            )

        compute_start = time_module.perf_counter()

        # Step 3: Enumerate tasks via Asana API
        try:
            tasks = await client.tasks.list_async(
                project=project_gid,
                opt_fields=_TASK_OPT_FIELDS,
            ).collect()
        except Exception:
            logger.exception(
                "timeline_task_enumeration_failed",
                extra={
                    "project_gid": project_gid,
                    "classifier_name": classifier_name,
                },
            )
            raise

        total_tasks = len(tasks)
        task_gids = [t.gid for t in tasks]

        # Step 4: Batch-read cached stories (pure-read, no API calls)
        stories_by_gid = read_stories_batch(task_gids, cache)

        # Step 4a: Bounded self-healing for story cache gaps
        # If a small number of tasks have no cached stories, fetch inline
        # to avoid partial results. Large gaps are logged but not fetched
        # inline (would blow ALB timeout).
        MAX_INLINE_STORY_FETCHES = 50
        misses = [gid for gid in task_gids if stories_by_gid.get(gid) is None]

        if 0 < len(misses) <= MAX_INLINE_STORY_FETCHES:
            sem = asyncio.Semaphore(5)

            async def _fetch_story(gid: str) -> None:
                async with sem:
                    try:
                        await client.stories.list_for_task_cached_async(gid)  # type: ignore[attr-defined]
                    except Exception:
                        logger.warning(
                            "inline_story_fetch_failed",
                            extra={"task_gid": gid},
                        )

            await asyncio.gather(*[_fetch_story(gid) for gid in misses])

            # Re-read batch after population
            stories_by_gid = read_stories_batch(task_gids, cache)

            fetched_count = sum(
                1 for gid in misses if stories_by_gid.get(gid) is not None
            )
            logger.info(
                "inline_story_fetch_complete",
                extra={
                    "project_gid": project_gid,
                    "miss_count": len(misses),
                    "fetched_count": fetched_count,
                },
            )
        elif len(misses) > MAX_INLINE_STORY_FETCHES:
            logger.warning(
                "story_cache_gap_above_threshold",
                extra={
                    "project_gid": project_gid,
                    "classifier_name": classifier_name,
                    "miss_count": len(misses),
                    "threshold": MAX_INLINE_STORY_FETCHES,
                },
            )

        # Step 5: Build timelines from cached stories
        timelines: list[SectionTimeline] = []  # type: ignore[no-redef]
        cache_hits = 0
        cache_misses = 0

        for task in tasks:
            task_gid = task.gid
            raw_stories = stories_by_gid.get(task_gid)

            task_created_at = _parse_datetime(task.created_at)
            section_name = extract_section_name(task, project_gid=project_gid)
            account_activity = (
                classifier.classify(section_name) if section_name else None
            )
            office_phone = _extract_office_phone(task.model_dump())

            if raw_stories is not None:
                cache_hits += 1
                # Convert raw dicts to Story models for filtering/building
                story_models = [Story.model_validate(s) for s in raw_stories]

                # Filter to section_changed only
                section_stories = [
                    s for s in story_models if s.resource_subtype == "section_changed"
                ]

                # Filter cross-project noise using the parameterized classifier
                filtered_stories = [
                    s
                    for s in section_stories
                    if not _is_cross_project_noise(s, classifier)
                ]

                # Sort by created_at ascending
                filtered_stories.sort(key=lambda s: s.created_at or "")

                # Build intervals
                intervals, story_count = _build_intervals_from_stories(
                    filtered_stories,
                    classifier=classifier,
                    entity_gid=task_gid,
                )

                # Handle never-moved task (imputation)
                if not intervals:
                    intervals = _build_imputed_interval(
                        task_created_at,
                        account_activity,
                        section_name or "UNKNOWN",
                    )
                    story_count = 0

                timelines.append(
                    SectionTimeline(
                        offer_gid=task_gid,
                        office_phone=office_phone,
                        intervals=tuple(intervals),
                        task_created_at=task_created_at,
                        story_count=story_count,
                    )
                )
            else:
                cache_misses += 1
                # Entity with zero cached stories.
                # Impute if task_created_at and current_section available.
                if task_created_at is not None and section_name is not None:
                    intervals = _build_imputed_interval(
                        task_created_at,
                        account_activity,
                        section_name,
                    )
                    if intervals:
                        timelines.append(
                            SectionTimeline(
                                offer_gid=task_gid,
                                office_phone=office_phone,
                                intervals=tuple(intervals),
                                task_created_at=task_created_at,
                                story_count=0,
                            )
                        )

        compute_duration_ms = (time_module.perf_counter() - compute_start) * 1000

        # Step 6: Store derived entry in cache
        timeline_data = [_serialize_timeline(t) for t in timelines]
        try:
            store_derived_timelines(
                project_gid=project_gid,
                classifier_name=classifier_name,
                timeline_data=timeline_data,
                cache=cache,
                entity_count=total_tasks,
                cache_hits=cache_hits,
                cache_misses=cache_misses,
                computation_duration_ms=compute_duration_ms,
            )
        except Exception:
            # Per TDD Section 8.2: Serialization error -- log and return
            # computed results (just not cached).
            logger.warning(
                "timeline_derived_cache_store_failed",
                extra={
                    "project_gid": project_gid,
                    "classifier_name": classifier_name,
                },
                exc_info=True,
            )

        logger.info(
            "timeline_computed_on_demand",
            extra={
                "project_gid": project_gid,
                "classifier_name": classifier_name,
                "total_tasks": total_tasks,
                "cache_hits": cache_hits,
                "cache_misses": cache_misses,
                "timelines_built": len(timelines),
                "duration_ms": round(compute_duration_ms, 1),
            },
        )

        # Step 7: Compute day counts and return
        return _compute_day_counts(
            timelines,
            period_start,
            period_end,
            classifier=classifier,
            classification_filter=classification_filter,
        )


def _compute_day_counts(
    timelines: list[SectionTimeline],
    period_start: date,
    period_end: date,
    classifier: SectionClassifier | None = None,
    classification_filter: str | None = None,
) -> list[OfferTimelineEntry]:
    """Compute day-count entries from deserialized timelines. Pure CPU, no I/O.

    Per TDD-SECTION-TIMELINE-REMEDIATION: Shared helper for computing
    OfferTimelineEntry results from a list of SectionTimeline objects.

    Derives current_section and current_classification from each timeline's
    last interval. When classification_filter is provided, only entries whose
    current_classification matches the filter value are included (O(n)
    post-cache filtering).

    Args:
        timelines: List of SectionTimeline domain objects.
        period_start: Query period start (inclusive).
        period_end: Query period end (inclusive).
        classifier: SectionClassifier for deriving current_classification.
            If None, current_classification is derived from the last
            interval's stored classification.
        classification_filter: If provided, only include entries whose
            current_classification matches this value (e.g., "active").

    Returns:
        List of OfferTimelineEntry with day counts for the requested period.
    """
    entries: list[OfferTimelineEntry] = []
    for timeline in timelines:
        # Derive current_section and current_classification from last interval
        current_section: str | None = None
        current_classification: str | None = None

        if timeline.intervals:
            last_interval = timeline.intervals[-1]
            current_section = last_interval.section_name

            if classifier is not None:
                cls = classifier.classify(current_section)
                current_classification = cls.value if cls is not None else None
            elif last_interval.classification is not None:
                current_classification = last_interval.classification.value

        # Apply classification filter (O(n) post-cache filtering)
        if classification_filter is not None:
            if current_classification != classification_filter:
                continue

        active_days = timeline.active_days_in_period(period_start, period_end)
        billable_days = timeline.billable_days_in_period(period_start, period_end)
        entries.append(
            OfferTimelineEntry(
                offer_gid=timeline.offer_gid,
                office_phone=timeline.office_phone,
                active_section_days=active_days,
                billable_section_days=billable_days,
                current_section=current_section,
                current_classification=current_classification,
            )
        )
    return entries
