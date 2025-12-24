"""Parallel section fetch for high-performance DataFrame construction.

Per TDD-WATERMARK-CACHE Phase 1: Provides parallel task fetching across
project sections to reduce cold-start latency from 52-59s to <10s.

Per ADR-0115: Uses section-parallel fetch with semaphore control.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from autom8_asana.dataframes.exceptions import DataFrameError

if TYPE_CHECKING:
    from autom8_asana.clients.sections import SectionsClient
    from autom8_asana.clients.tasks import TasksClient
    from autom8_asana.models.section import Section
    from autom8_asana.models.task import Task


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
    _api_call_count: int = field(default=0, init=False, repr=False)

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
        """List all sections in the project.

        Returns:
            List of Section objects.
        """
        sections: list[Section] = await self.sections_client.list_for_project_async(
            self.project_gid
        ).collect()
        return sections

    async def fetch_section_task_gids_async(self) -> dict[str, list[str]]:
        """Enumerate task GIDs per section without full task data.

        Per TDD-CACHE-PERF-FETCH-PATH Phase 2: Lightweight enumeration
        for cache key lookup before full fetch. Uses minimal opt_fields
        (just 'gid') for efficiency.

        Returns:
            Dict mapping section_gid -> list of task_gids in that section.
            Empty dict if project has no sections.

        Raises:
            ParallelFetchError: If GID enumeration fails (caller should fallback).
        """
        self._api_call_count = 0

        # Enumerate sections
        sections = await self._list_sections()
        self._api_call_count += 1

        if not sections:
            return {}

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)

        # Fetch GIDs from all sections concurrently
        results = await asyncio.gather(
            *[
                self._fetch_section_gids(section.gid, semaphore)
                for section in sections
            ],
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

        return section_gids

    async def _fetch_section_gids(
        self,
        section_gid: str,
        semaphore: asyncio.Semaphore,
    ) -> list[str]:
        """Fetch task GIDs from a single section (lightweight).

        Uses minimal opt_fields=['gid'] for efficiency.

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
                opt_fields=["gid"],  # Minimal fields for efficiency
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
            *[self._fetch_section(section_gid, semaphore) for section_gid in sections_to_fetch],
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
