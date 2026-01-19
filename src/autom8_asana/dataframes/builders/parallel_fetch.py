"""Parallel section fetch for high-performance DataFrame construction.

Per TDD-WATERMARK-CACHE Phase 1: Provides parallel task fetching across
project sections to reduce cold-start latency from 52-59s to <10s.

Per ADR-0115: Uses section-parallel fetch with semaphore control.

Per PRD-CACHE-OPT-P3 / ADR-0131: GID enumeration caching for 10x speedup.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar

from autom8y_log import get_logger

from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.dataframes.exceptions import DataFrameError

if TYPE_CHECKING:
    from autom8_asana.clients.sections import SectionsClient
    from autom8_asana.clients.tasks import TasksClient
    from autom8_asana.models.section import Section
    from autom8_asana.models.task import Task
    from autom8_asana.protocols.cache import CacheProvider

logger = get_logger(__name__)


class ParallelFetchError(DataFrameError):
    """Parallel section fetch failed.

    Per FR-FALLBACK-004: Raised when one or more section fetches fail.
    Caller should fall back to serial project-level fetch.

    Attributes:
        errors: List of exceptions from failed section fetches.
        section_gids: GIDs of sections that failed.
    """

    def __init__(
        self,
        message: str,
        *,
        errors: list[Exception] | None = None,
        section_gids: list[str] | None = None,
    ) -> None:
        super().__init__(
            message,
            context={
                "error_count": len(errors) if errors else 0,
                "section_gids": section_gids or [],
            },
        )
        self.errors = errors or []
        self.section_gids = section_gids or []


@dataclass
class FetchResult:
    """Result of parallel section fetch.

    Per TDD-WATERMARK-CACHE: Provides metadata about the fetch operation
    for observability and debugging.

    Attributes:
        tasks: Deduplicated list of tasks from all sections.
        sections_fetched: Number of sections successfully fetched.
        total_api_calls: Total API calls made (1 for section list + N for tasks).
        fetch_time_ms: Total fetch time in milliseconds.
    """

    tasks: list[Task]
    sections_fetched: int
    total_api_calls: int
    fetch_time_ms: float


@dataclass
class ParallelSectionFetcher:
    """Coordinates parallel task fetching across project sections.

    Per FR-FETCH-003: Concurrent section fetches using asyncio.gather().
    Per FR-FETCH-004: Configurable concurrency limit via semaphore.
    Per FR-FETCH-006: Deduplication of multi-homed tasks by GID.

    This is an internal implementation detail, not part of public API.

    Attributes:
        sections_client: Client for section operations.
        tasks_client: Client for task operations.
        project_gid: GID of the project to fetch from.
        max_concurrent: Maximum concurrent section fetches (default 8).
        opt_fields: Optional fields to include in task responses.

    Example:
        >>> fetcher = ParallelSectionFetcher(
        ...     sections_client=client.sections,
        ...     tasks_client=client.tasks,
        ...     project_gid="1234567890",
        ...     max_concurrent=8,
        ... )
        >>> result = await fetcher.fetch_all()
        >>> print(f"Fetched {len(result.tasks)} tasks in {result.fetch_time_ms}ms")
    """

    sections_client: SectionsClient
    tasks_client: TasksClient
    project_gid: str
    max_concurrent: int = 8
    opt_fields: list[str] | None = None
    cache_provider: CacheProvider | None = None  # Per ADR-0131: GID enumeration caching
    _api_call_count: int = field(default=0, init=False, repr=False)

    # TTL constants per PRD-CACHE-OPT-P3
    _SECTIONS_TTL: ClassVar[int] = 1800  # 30 minutes
    _GID_ENUM_TTL: ClassVar[int] = 300  # 5 minutes

    async def fetch_all(self) -> FetchResult:
        """Fetch all tasks via parallel section fetch.

        Per FR-FETCH-002: Enumerates sections via list_for_project_async().
        Per FR-FETCH-003: Fetches tasks concurrently using asyncio.gather().
        Per FR-FETCH-005: Skips empty sections without error.
        Per FR-FETCH-006: Deduplicates by task GID.
        Per FR-FETCH-008: Falls back to project-level fetch if no sections.
        Per FR-FALLBACK-004: Uses return_exceptions=True to detect failures.

        Returns:
            FetchResult with tasks and metadata.

        Raises:
            ParallelFetchError: If parallel fetch fails (caller should fallback).
        """
        start_time = time.perf_counter()
        self._api_call_count = 0

        # FR-FETCH-002: Enumerate sections
        sections = await self._list_sections()
        self._api_call_count += 1  # Section list call

        # FR-FETCH-008: Handle projects with no sections
        if not sections:
            # Return empty result - caller will fall back to project-level fetch
            end_time = time.perf_counter()
            return FetchResult(
                tasks=[],
                sections_fetched=0,
                total_api_calls=self._api_call_count,
                fetch_time_ms=(end_time - start_time) * 1000,
            )

        # FR-FETCH-004: Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)

        # FR-FETCH-003: Fetch tasks from all sections concurrently
        # FR-FALLBACK-004: Use return_exceptions=True to detect failures
        results = await asyncio.gather(
            *[self._fetch_section(section.gid, semaphore) for section in sections],
            return_exceptions=True,
        )

        # Check for exceptions - fail all if any failed
        errors: list[Exception] = []
        failed_section_gids: list[str] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(result)
                failed_section_gids.append(sections[i].gid)

        if errors:
            raise ParallelFetchError(
                f"Parallel section fetch failed: {len(errors)} section(s) failed",
                errors=errors,
                section_gids=failed_section_gids,
            )

        # Flatten and deduplicate tasks by GID (FR-FETCH-006)
        all_tasks: list[Task] = []
        seen_gids: set[str] = set()

        for section_tasks in results:
            # Type narrowing: we know these aren't exceptions after the check above
            assert isinstance(section_tasks, list)
            for task in section_tasks:
                if task.gid not in seen_gids:
                    seen_gids.add(task.gid)
                    all_tasks.append(task)

        end_time = time.perf_counter()

        return FetchResult(
            tasks=all_tasks,
            sections_fetched=len(sections),
            total_api_calls=self._api_call_count,
            fetch_time_ms=(end_time - start_time) * 1000,
        )

    async def _list_sections(self) -> list[Section]:
        """List all sections in the project with caching.

        Per FR-SECTION-001/002/003: Checks cache before API call,
        populates cache on miss.

        Returns:
            List of Section objects.
        """
        # FR-SECTION-001: Check cache first
        cached_sections = self._get_cached_sections()
        if cached_sections is not None:
            return cached_sections

        # Cache miss - fetch from API
        sections: list[Section] = await self.sections_client.list_for_project_async(
            self.project_gid
        ).collect()

        # FR-SECTION-003: Populate cache on miss
        self._cache_sections(sections)

        return sections

    def _make_cache_key(self, suffix: str) -> str:
        """Generate cache key for this project.

        Args:
            suffix: Key suffix ("sections" or "gid_enumeration")

        Returns:
            Formatted cache key, e.g., "project:1234567890:sections"
        """
        return f"project:{self.project_gid}:{suffix}"

    def _get_cached_sections(self) -> list[Section] | None:
        """Attempt to retrieve sections from cache.

        Per FR-DEGRADE-001: Graceful degradation on cache failure.
        Per FR-DEGRADE-003: When cache_provider=None, bypass caching entirely.

        Returns:
            Cached sections if hit and not expired, None on miss or error.
        """
        if self.cache_provider is None:
            return None

        try:
            key = self._make_cache_key("sections")
            entry = self.cache_provider.get_versioned(key, EntryType.PROJECT_SECTIONS)

            if entry is None:
                logger.debug(
                    "section_list_cache_miss",
                    extra={"project_gid": self.project_gid, "reason": "not_found"},
                )
                return None

            if entry.is_expired():
                logger.debug(
                    "section_list_cache_miss",
                    extra={"project_gid": self.project_gid, "reason": "expired"},
                )
                return None

            # Convert cached data back to Section objects
            from autom8_asana.models.section import Section

            sections = [
                Section(gid=s["gid"], name=s["name"])
                for s in entry.data.get("sections", [])
            ]

            logger.debug(
                "section_list_cache_hit",
                extra={
                    "project_gid": self.project_gid,
                    "section_count": len(sections),
                    "api_calls_saved": 1,
                },
            )
            return sections

        except Exception as e:
            # FR-DEGRADE-001: Graceful degradation
            logger.warning(
                "section_list_cache_lookup_failed",
                extra={
                    "project_gid": self.project_gid,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            return None

    def _cache_sections(self, sections: list[Section]) -> None:
        """Populate cache with section list.

        Per FR-DEGRADE-002: Cache failure does not prevent operation.
        Per FR-DEGRADE-003: When cache_provider=None, bypass caching entirely.

        Args:
            sections: List of Section objects to cache.
        """
        if self.cache_provider is None:
            return

        try:
            key = self._make_cache_key("sections")
            entry = CacheEntry(
                key=key,
                data={"sections": [{"gid": s.gid, "name": s.name} for s in sections]},
                entry_type=EntryType.PROJECT_SECTIONS,
                version=datetime.now(UTC),
                cached_at=datetime.now(UTC),
                ttl=self._SECTIONS_TTL,
                project_gid=self.project_gid,
                metadata={"section_count": len(sections)},
            )
            self.cache_provider.set_versioned(key, entry)

            logger.debug(
                "section_list_cache_populated",
                extra={
                    "project_gid": self.project_gid,
                    "section_count": len(sections),
                },
            )

        except Exception as e:
            # FR-DEGRADE-002: Cache failure does not prevent operation
            logger.warning(
                "section_list_cache_population_failed",
                extra={
                    "project_gid": self.project_gid,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )

    async def fetch_section_task_gids_async(self) -> dict[str, list[str]]:
        """Enumerate task GIDs per section without full task data.

        Per TDD-CACHE-PERF-FETCH-PATH Phase 2: Lightweight enumeration
        for cache key lookup before full fetch. Uses minimal opt_fields
        (just 'gid') for efficiency.

        Per PRD-CACHE-OPT-P3 / FR-GID-001/002/003: Checks cache before API calls,
        populates cache on miss.

        Returns:
            Dict mapping section_gid -> list of task_gids in that section.
            Empty dict if project has no sections.

        Raises:
            ParallelFetchError: If GID enumeration fails (caller should fallback).
        """
        self._api_call_count = 0

        # FR-GID-001: Check GID enumeration cache first
        cached_result = self._get_cached_gid_enumeration()
        if cached_result is not None:
            return cached_result

        # Cache miss - enumerate sections
        sections = await self._list_sections()
        self._api_call_count += 1

        if not sections:
            return {}

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)

        # Fetch GIDs from all sections concurrently
        results = await asyncio.gather(
            *[self._fetch_section_gids(section.gid, semaphore) for section in sections],
            return_exceptions=True,
        )

        # Check for exceptions
        errors: list[Exception] = []
        failed_section_gids: list[str] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(result)
                failed_section_gids.append(sections[i].gid)

        if errors:
            raise ParallelFetchError(
                f"GID enumeration failed: {len(errors)} section(s) failed",
                errors=errors,
                section_gids=failed_section_gids,
            )

        # Build result mapping
        section_gids: dict[str, list[str]] = {}
        for i, section in enumerate(sections):
            gid_list = results[i]
            assert isinstance(gid_list, list)
            section_gids[section.gid] = gid_list

        # FR-GID-003: Populate cache on miss
        self._cache_gid_enumeration(section_gids)

        return section_gids

    def _get_cached_gid_enumeration(self) -> dict[str, list[str]] | None:
        """Attempt to retrieve GID enumeration from cache.

        Per FR-DEGRADE-001: Graceful degradation on cache failure.
        Per FR-DEGRADE-003: When cache_provider=None, bypass caching entirely.

        Returns:
            Cached mapping if hit and not expired, None on miss or error.
        """
        if self.cache_provider is None:
            return None

        try:
            key = self._make_cache_key("gid_enumeration")
            entry = self.cache_provider.get_versioned(key, EntryType.GID_ENUMERATION)

            if entry is None:
                logger.debug(
                    "gid_enumeration_cache_miss",
                    extra={"project_gid": self.project_gid, "reason": "not_found"},
                )
                return None

            if entry.is_expired():
                logger.debug(
                    "gid_enumeration_cache_miss",
                    extra={"project_gid": self.project_gid, "reason": "expired"},
                )
                return None

            section_gids: dict[str, list[str]] = entry.data.get("section_gids", {})
            total_gids = sum(len(gids) for gids in section_gids.values())

            logger.info(
                "gid_enumeration_cache_hit",
                extra={
                    "project_gid": self.project_gid,
                    "section_count": len(section_gids),
                    "gid_count": total_gids,
                    "api_calls_saved": len(section_gids) + 1,
                },
            )
            return section_gids

        except Exception as e:
            # FR-DEGRADE-001: Graceful degradation
            logger.warning(
                "gid_enumeration_cache_lookup_failed",
                extra={
                    "project_gid": self.project_gid,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            return None

    def _cache_gid_enumeration(
        self,
        section_gids: dict[str, list[str]],
    ) -> None:
        """Populate cache with GID enumeration.

        Per FR-DEGRADE-002: Cache failure does not prevent operation.
        Per FR-DEGRADE-003: When cache_provider=None, bypass caching entirely.

        Args:
            section_gids: Dict mapping section_gid -> task_gids.
        """
        if self.cache_provider is None:
            return

        try:
            key = self._make_cache_key("gid_enumeration")
            total_gids = sum(len(gids) for gids in section_gids.values())

            entry = CacheEntry(
                key=key,
                data={"section_gids": section_gids},
                entry_type=EntryType.GID_ENUMERATION,
                version=datetime.now(UTC),
                cached_at=datetime.now(UTC),
                ttl=self._GID_ENUM_TTL,
                project_gid=self.project_gid,
                metadata={
                    "section_count": len(section_gids),
                    "total_gid_count": total_gids,
                },
            )
            self.cache_provider.set_versioned(key, entry)

            logger.debug(
                "gid_enumeration_cache_populated",
                extra={
                    "project_gid": self.project_gid,
                    "section_count": len(section_gids),
                    "gid_count": total_gids,
                },
            )

        except Exception as e:
            # FR-DEGRADE-002: Cache failure does not prevent operation
            logger.warning(
                "gid_enumeration_cache_population_failed",
                extra={
                    "project_gid": self.project_gid,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )

    async def _fetch_section_gids(
        self,
        section_gid: str,
        semaphore: asyncio.Semaphore,
    ) -> list[str]:
        """Fetch task GIDs from a single section (lightweight).

        Uses minimal opt_fields=['gid'] for efficiency.

        Per TDD-CACHE-COMPLETENESS-001 Phase 3: This method intentionally
        does NOT cache task data in UnifiedTaskStore. Caching GID-only entries
        would create MINIMAL completeness entries that downstream consumers
        (CascadeViewPlugin, DataFrameViewPlugin) cannot use for extraction.
        Task data caching with proper completeness tracking is handled by
        the caller (ProjectDataFrameBuilder).

        Args:
            section_gid: GID of the section to fetch.
            semaphore: Semaphore for concurrency control.

        Returns:
            List of task GID strings from the section.
        """
        async with semaphore:
            self._api_call_count += 1
            tasks: list[Task] = await self.tasks_client.list_async(
                section=section_gid,
                opt_fields=[
                    "gid"
                ],  # Minimal fields for efficiency - NOT cached as task data
            ).collect()
            return [task.gid for task in tasks if task.gid]

    async def _fetch_section(
        self,
        section_gid: str,
        semaphore: asyncio.Semaphore,
    ) -> list[Task]:
        """Fetch tasks from a single section with semaphore control.

        Per FR-FETCH-004: Uses semaphore to limit concurrent requests.
        Per FR-FETCH-005: Returns empty list for sections with no tasks.
        Per FR-FETCH-007: Passes opt_fields to task fetch.

        Per TDD-CACHE-COMPLETENESS-001 Phase 3: Tasks are fetched with
        self.opt_fields (typically _BASE_OPT_FIELDS for STANDARD completeness).
        The caller is responsible for caching with proper completeness
        tracking by passing opt_fields to UnifiedTaskStore.put_batch_async().

        Args:
            section_gid: GID of the section to fetch.
            semaphore: Semaphore for concurrency control.

        Returns:
            List of Task objects from the section.
        """
        async with semaphore:
            self._api_call_count += 1
            tasks: list[Task] = await self.tasks_client.list_async(
                section=section_gid,
                opt_fields=self.opt_fields,
            ).collect()
            return tasks

    async def fetch_by_gids(
        self,
        task_gids: list[str],
        section_gid_map: dict[str, list[str]] | None = None,
    ) -> FetchResult:
        """Fetch only specified task GIDs from the project.

        Per FR-MISS-002 (TDD-CACHE-OPTIMIZATION-P2): Targeted fetch for cache
        misses only, avoiding full re-fetch of all section tasks.

        Strategy:
        - If section_gid_map provided, filter to sections containing target GIDs
        - Fetch only those sections, filter results to target GIDs
        - More efficient than N individual get_async() calls

        Args:
            task_gids: List of task GIDs to fetch.
            section_gid_map: Optional mapping of section_gid -> task_gids.
                If provided, used to determine which sections to query.
                If None, queries all sections and filters.

        Returns:
            FetchResult containing only the requested tasks.

        Raises:
            ParallelFetchError: If fetch fails (caller should fallback).

        Example:
            >>> miss_gids = ["task1", "task3"]
            >>> result = await fetcher.fetch_by_gids(miss_gids, section_gid_map)
            >>> assert all(t.gid in miss_gids for t in result.tasks)
        """
        import time

        start_time = time.perf_counter()
        self._api_call_count = 0

        if not task_gids:
            return FetchResult(
                tasks=[],
                sections_fetched=0,
                total_api_calls=0,
                fetch_time_ms=0.0,
            )

        target_gid_set = set(task_gids)

        # Determine which sections to fetch
        if section_gid_map is not None:
            # Find sections containing target GIDs
            sections_to_fetch = [
                section_gid
                for section_gid, gids in section_gid_map.items()
                if any(gid in target_gid_set for gid in gids)
            ]
        else:
            # No section map - enumerate sections first
            sections = await self._list_sections()
            self._api_call_count += 1
            sections_to_fetch = [s.gid for s in sections]

        if not sections_to_fetch:
            end_time = time.perf_counter()
            return FetchResult(
                tasks=[],
                sections_fetched=0,
                total_api_calls=self._api_call_count,
                fetch_time_ms=(end_time - start_time) * 1000,
            )

        # Fetch tasks from relevant sections
        semaphore = asyncio.Semaphore(self.max_concurrent)

        results = await asyncio.gather(
            *[
                self._fetch_section(section_gid, semaphore)
                for section_gid in sections_to_fetch
            ],
            return_exceptions=True,
        )

        # Check for exceptions
        errors: list[Exception] = []
        failed_section_gids: list[str] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(result)
                failed_section_gids.append(sections_to_fetch[i])

        if errors:
            raise ParallelFetchError(
                f"Targeted fetch failed: {len(errors)} section(s) failed",
                errors=errors,
                section_gids=failed_section_gids,
            )

        # Filter to only target GIDs, deduplicate by GID
        filtered_tasks: list[Task] = []
        seen_gids: set[str] = set()

        for section_tasks in results:
            assert isinstance(section_tasks, list)
            for task in section_tasks:
                if task.gid in target_gid_set and task.gid not in seen_gids:
                    seen_gids.add(task.gid)
                    filtered_tasks.append(task)

        end_time = time.perf_counter()

        return FetchResult(
            tasks=filtered_tasks,
            sections_fetched=len(sections_to_fetch),
            total_api_calls=self._api_call_count,
            fetch_time_ms=(end_time - start_time) * 1000,
        )
