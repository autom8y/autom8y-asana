"""Tests for ParallelSectionFetcher.

Per TDD-WATERMARK-CACHE Phase 1: Unit tests for parallel section fetch
covering success paths, error handling, and deduplication.
"""

from __future__ import annotations

import asyncio
from datetime import UTC
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.dataframes.builders.parallel_fetch import (
    FetchResult,
    ParallelFetchError,
    ParallelSectionFetcher,
)
from autom8_asana.models.section import Section
from autom8_asana.models.task import Task

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_section() -> Section:
    """Create a mock Section for testing."""
    return Section(gid="section_1", name="Test Section")


@pytest.fixture
def mock_sections() -> list[Section]:
    """Create multiple mock Sections for testing."""
    return [
        Section(gid="section_1", name="Section 1"),
        Section(gid="section_2", name="Section 2"),
        Section(gid="section_3", name="Section 3"),
    ]


@pytest.fixture
def mock_task() -> Task:
    """Create a minimal Task for testing."""
    return Task(
        gid="task_1",
        name="Test Task",
        resource_subtype="default_task",
        completed=False,
        created_at="2024-01-15T10:30:00.000Z",
        modified_at="2024-01-16T15:45:30.000Z",
    )


@pytest.fixture
def mock_tasks_by_section() -> dict[str, list[Task]]:
    """Create tasks organized by section GID."""
    return {
        "section_1": [
            Task(
                gid="task_1",
                name="Task 1",
                resource_subtype="default_task",
                completed=False,
                created_at="2024-01-15T10:30:00.000Z",
                modified_at="2024-01-16T15:45:30.000Z",
            ),
            Task(
                gid="task_2",
                name="Task 2",
                resource_subtype="default_task",
                completed=False,
                created_at="2024-01-15T10:30:00.000Z",
                modified_at="2024-01-16T15:45:30.000Z",
            ),
        ],
        "section_2": [
            Task(
                gid="task_3",
                name="Task 3",
                resource_subtype="default_task",
                completed=False,
                created_at="2024-01-15T10:30:00.000Z",
                modified_at="2024-01-16T15:45:30.000Z",
            ),
        ],
        "section_3": [],  # Empty section
    }


@pytest.fixture
def multi_homed_tasks() -> dict[str, list[Task]]:
    """Create tasks where some appear in multiple sections (multi-homed)."""
    shared_task = Task(
        gid="shared_task",
        name="Shared Task",
        resource_subtype="default_task",
        completed=False,
        created_at="2024-01-15T10:30:00.000Z",
        modified_at="2024-01-16T15:45:30.000Z",
    )
    return {
        "section_1": [
            Task(
                gid="task_1",
                name="Task 1",
                resource_subtype="default_task",
                completed=False,
                created_at="2024-01-15T10:30:00.000Z",
                modified_at="2024-01-16T15:45:30.000Z",
            ),
            shared_task,
        ],
        "section_2": [
            shared_task,  # Same task appears in section_2
            Task(
                gid="task_2",
                name="Task 2",
                resource_subtype="default_task",
                completed=False,
                created_at="2024-01-15T10:30:00.000Z",
                modified_at="2024-01-16T15:45:30.000Z",
            ),
        ],
    }


def create_mock_sections_client(sections: list[Section]) -> MagicMock:
    """Create a mock SectionsClient that returns the given sections."""
    mock_client = MagicMock()

    # Create a mock PageIterator
    mock_iterator = MagicMock()
    mock_iterator.collect = AsyncMock(return_value=sections)

    mock_client.list_for_project_async = MagicMock(return_value=mock_iterator)
    return mock_client


def create_mock_tasks_client(
    tasks_by_section: dict[str, list[Task]],
) -> MagicMock:
    """Create a mock TasksClient that returns tasks based on section GID."""
    mock_client = MagicMock()

    def create_iterator(section: str | None = None, **kwargs: Any) -> MagicMock:
        mock_iterator = MagicMock()
        tasks = tasks_by_section.get(section, []) if section else []
        mock_iterator.collect = AsyncMock(return_value=tasks)
        return mock_iterator

    mock_client.list_async = MagicMock(side_effect=create_iterator)
    return mock_client


# =============================================================================
# TestParallelSectionFetcher
# =============================================================================


class TestParallelSectionFetcher:
    """Tests for ParallelSectionFetcher class."""

    # -------------------------------------------------------------------------
    # Success Cases
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_fetch_all_success(
        self,
        mock_sections: list[Section],
        mock_tasks_by_section: dict[str, list[Task]],
    ) -> None:
        """Test successful parallel fetch of all sections."""
        sections_client = create_mock_sections_client(mock_sections)
        tasks_client = create_mock_tasks_client(mock_tasks_by_section)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
            max_concurrent=8,
        )

        result = await fetcher.fetch_all()

        assert isinstance(result, FetchResult)
        assert len(result.tasks) == 3  # task_1, task_2, task_3
        assert result.sections_fetched == 3
        assert result.total_api_calls == 4  # 1 section list + 3 section fetches
        assert result.fetch_time_ms > 0

    @pytest.mark.asyncio
    async def test_fetch_all_empty_project(self) -> None:
        """Test fetch_all with project that has no sections."""
        sections_client = create_mock_sections_client([])
        tasks_client = create_mock_tasks_client({})

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
        )

        result = await fetcher.fetch_all()

        assert isinstance(result, FetchResult)
        assert len(result.tasks) == 0
        assert result.sections_fetched == 0
        assert result.total_api_calls == 1  # Only section list call

    @pytest.mark.asyncio
    async def test_fetch_all_empty_sections(
        self,
        mock_sections: list[Section],
    ) -> None:
        """Test fetch_all where all sections have no tasks."""
        # All sections return empty task lists
        tasks_by_section = {
            "section_1": [],
            "section_2": [],
            "section_3": [],
        }
        sections_client = create_mock_sections_client(mock_sections)
        tasks_client = create_mock_tasks_client(tasks_by_section)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
        )

        result = await fetcher.fetch_all()

        assert len(result.tasks) == 0
        assert result.sections_fetched == 3

    @pytest.mark.asyncio
    async def test_fetch_all_multi_homed_dedup(
        self,
        multi_homed_tasks: dict[str, list[Task]],
    ) -> None:
        """Test deduplication of multi-homed tasks appearing in multiple sections."""
        sections = [
            Section(gid="section_1", name="Section 1"),
            Section(gid="section_2", name="Section 2"),
        ]
        sections_client = create_mock_sections_client(sections)
        tasks_client = create_mock_tasks_client(multi_homed_tasks)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
        )

        result = await fetcher.fetch_all()

        # Should have 3 unique tasks: task_1, shared_task, task_2
        assert len(result.tasks) == 3
        task_gids = {task.gid for task in result.tasks}
        assert task_gids == {"task_1", "shared_task", "task_2"}

    # -------------------------------------------------------------------------
    # Concurrency Control
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_fetch_all_semaphore_limits(self) -> None:
        """Test that semaphore limits concurrent requests."""
        # Create many sections to test concurrency
        many_sections = [
            Section(gid=f"section_{i}", name=f"Section {i}") for i in range(20)
        ]

        sections_client = create_mock_sections_client(many_sections)

        # Track concurrent requests
        concurrent_count = 0
        max_concurrent_observed = 0
        lock = asyncio.Lock()

        async def track_concurrency_collect():
            """Mock collect method that tracks concurrency."""
            nonlocal concurrent_count, max_concurrent_observed
            async with lock:
                concurrent_count += 1
                if concurrent_count > max_concurrent_observed:
                    max_concurrent_observed = concurrent_count

            # Simulate some async work
            await asyncio.sleep(0.01)

            async with lock:
                concurrent_count -= 1

            return []

        def create_tracking_iterator(
            section: str | None = None, **kwargs: Any
        ) -> MagicMock:
            """Create a mock iterator that tracks concurrency on collect."""
            mock_iterator = MagicMock()
            mock_iterator.collect = track_concurrency_collect
            return mock_iterator

        tasks_client = MagicMock()
        tasks_client.list_async = MagicMock(side_effect=create_tracking_iterator)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
            max_concurrent=4,  # Limit to 4 concurrent
        )

        await fetcher.fetch_all()

        # Verify semaphore limited concurrency
        assert max_concurrent_observed <= 4

    # -------------------------------------------------------------------------
    # Error Handling
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_fetch_all_partial_failure(
        self,
        mock_sections: list[Section],
    ) -> None:
        """Test that partial section failure raises ParallelFetchError."""
        sections_client = create_mock_sections_client(mock_sections)

        # Create tasks client where one section fails
        tasks_client = MagicMock()

        call_count = 0

        def create_iterator_with_failure(
            section: str | None = None, **kwargs: Any
        ) -> MagicMock:
            nonlocal call_count
            call_count += 1
            mock_iterator = MagicMock()

            if section == "section_2":
                # This section fails
                mock_iterator.collect = AsyncMock(
                    side_effect=Exception("API Error: Rate limit exceeded")
                )
            else:
                mock_iterator.collect = AsyncMock(return_value=[])

            return mock_iterator

        tasks_client.list_async = MagicMock(side_effect=create_iterator_with_failure)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
        )

        with pytest.raises(ParallelFetchError) as exc_info:
            await fetcher.fetch_all()

        assert len(exc_info.value.errors) == 1
        assert "section_2" in exc_info.value.section_gids

    @pytest.mark.asyncio
    async def test_fetch_all_multiple_failures(
        self,
        mock_sections: list[Section],
    ) -> None:
        """Test that multiple section failures are all reported."""
        sections_client = create_mock_sections_client(mock_sections)

        # Create tasks client where multiple sections fail
        tasks_client = MagicMock()

        def create_failing_iterator(
            section: str | None = None, **kwargs: Any
        ) -> MagicMock:
            mock_iterator = MagicMock()
            if section in ("section_1", "section_3"):
                mock_iterator.collect = AsyncMock(side_effect=Exception("API Error"))
            else:
                mock_iterator.collect = AsyncMock(return_value=[])
            return mock_iterator

        tasks_client.list_async = MagicMock(side_effect=create_failing_iterator)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
        )

        with pytest.raises(ParallelFetchError) as exc_info:
            await fetcher.fetch_all()

        assert len(exc_info.value.errors) == 2
        assert set(exc_info.value.section_gids) == {"section_1", "section_3"}

    # -------------------------------------------------------------------------
    # API Call Counting
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_fetch_all_counts_api_calls(
        self,
        mock_sections: list[Section],
        mock_tasks_by_section: dict[str, list[Task]],
    ) -> None:
        """Test that API call count is accurate."""
        sections_client = create_mock_sections_client(mock_sections)
        tasks_client = create_mock_tasks_client(mock_tasks_by_section)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
        )

        result = await fetcher.fetch_all()

        # 1 call for section list + 3 calls for section tasks
        assert result.total_api_calls == 4

    # -------------------------------------------------------------------------
    # Opt Fields
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_fetch_all_passes_opt_fields(
        self,
        mock_sections: list[Section],
        mock_tasks_by_section: dict[str, list[Task]],
    ) -> None:
        """Test that opt_fields are passed to task fetch."""
        sections_client = create_mock_sections_client(mock_sections)
        tasks_client = create_mock_tasks_client(mock_tasks_by_section)

        opt_fields = ["name", "notes", "custom_fields"]

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
            opt_fields=opt_fields,
        )

        await fetcher.fetch_all()

        # Verify opt_fields were passed to each list_async call
        for call in tasks_client.list_async.call_args_list:
            assert call.kwargs.get("opt_fields") == opt_fields


# =============================================================================
# TestFetchResult
# =============================================================================


class TestFetchResult:
    """Tests for FetchResult dataclass."""

    def test_fetch_result_creation(self) -> None:
        """Test FetchResult can be created with required fields."""
        result = FetchResult(
            tasks=[],
            sections_fetched=5,
            total_api_calls=6,
            fetch_time_ms=1234.56,
        )

        assert result.tasks == []
        assert result.sections_fetched == 5
        assert result.total_api_calls == 6
        assert result.fetch_time_ms == 1234.56


# =============================================================================
# TestParallelFetchError
# =============================================================================


class TestParallelFetchError:
    """Tests for ParallelFetchError exception."""

    def test_error_creation_minimal(self) -> None:
        """Test ParallelFetchError with minimal arguments."""
        error = ParallelFetchError("Fetch failed")

        assert str(error) == "Fetch failed"
        assert error.errors == []
        assert error.section_gids == []

    def test_error_creation_with_details(self) -> None:
        """Test ParallelFetchError with full details."""
        errors = [Exception("Error 1"), Exception("Error 2")]
        section_gids = ["section_1", "section_2"]

        error = ParallelFetchError(
            "Multiple sections failed",
            errors=errors,
            section_gids=section_gids,
        )

        assert len(error.errors) == 2
        assert error.section_gids == section_gids
        assert error.context["error_count"] == 2
        assert error.context["section_gids"] == section_gids


# =============================================================================
# TestFetchSectionTaskGidsAsync
# =============================================================================


class TestFetchSectionTaskGidsAsync:
    """Tests for ParallelSectionFetcher.fetch_section_task_gids_async().

    Per TDD-CACHE-PERF-FETCH-PATH Phase 2: Lightweight GID enumeration.
    """

    @pytest.mark.asyncio
    async def test_fetch_gids_success(
        self,
        mock_sections: list[Section],
        mock_tasks_by_section: dict[str, list[Task]],
    ) -> None:
        """Test successful GID enumeration returns correct mapping."""
        sections_client = create_mock_sections_client(mock_sections)
        tasks_client = create_mock_tasks_client(mock_tasks_by_section)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
            max_concurrent=8,
        )

        result = await fetcher.fetch_section_task_gids_async()

        # Should have mapping for all sections
        assert len(result) == 3
        assert "section_1" in result
        assert "section_2" in result
        assert "section_3" in result

        # Verify GID lists
        assert result["section_1"] == ["task_1", "task_2"]
        assert result["section_2"] == ["task_3"]
        assert result["section_3"] == []  # Empty section

    @pytest.mark.asyncio
    async def test_fetch_gids_empty_project(self) -> None:
        """Test GID enumeration with project that has no sections."""
        sections_client = create_mock_sections_client([])
        tasks_client = create_mock_tasks_client({})

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
        )

        result = await fetcher.fetch_section_task_gids_async()

        assert result == {}

    @pytest.mark.asyncio
    async def test_fetch_gids_uses_minimal_opt_fields(
        self,
        mock_sections: list[Section],
        mock_tasks_by_section: dict[str, list[Task]],
    ) -> None:
        """Test GID enumeration uses minimal opt_fields for efficiency."""
        sections_client = create_mock_sections_client(mock_sections)
        tasks_client = create_mock_tasks_client(mock_tasks_by_section)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
            opt_fields=["name", "notes", "custom_fields"],  # Full opt_fields
        )

        await fetcher.fetch_section_task_gids_async()

        # Verify opt_fields were ['gid'] for lightweight fetch
        for call in tasks_client.list_async.call_args_list:
            assert call.kwargs.get("opt_fields") == ["gid"]

    @pytest.mark.asyncio
    async def test_fetch_gids_handles_multi_homed(
        self,
        multi_homed_tasks: dict[str, list[Task]],
    ) -> None:
        """Test GID enumeration handles multi-homed tasks (same GID in multiple sections)."""
        sections = [
            Section(gid="section_1", name="Section 1"),
            Section(gid="section_2", name="Section 2"),
        ]
        sections_client = create_mock_sections_client(sections)
        tasks_client = create_mock_tasks_client(multi_homed_tasks)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
        )

        result = await fetcher.fetch_section_task_gids_async()

        # Each section should list all its GIDs (including shared)
        assert "shared_task" in result["section_1"]
        assert "shared_task" in result["section_2"]

    @pytest.mark.asyncio
    async def test_fetch_gids_partial_failure(
        self,
        mock_sections: list[Section],
    ) -> None:
        """Test GID enumeration raises ParallelFetchError on partial failure."""
        sections_client = create_mock_sections_client(mock_sections)

        tasks_client = MagicMock()

        def create_iterator_with_failure(
            section: str | None = None, **kwargs: Any
        ) -> MagicMock:
            mock_iterator = MagicMock()
            if section == "section_2":
                mock_iterator.collect = AsyncMock(side_effect=Exception("API Error"))
            else:
                mock_iterator.collect = AsyncMock(return_value=[])
            return mock_iterator

        tasks_client.list_async = MagicMock(side_effect=create_iterator_with_failure)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
        )

        with pytest.raises(ParallelFetchError) as exc_info:
            await fetcher.fetch_section_task_gids_async()

        assert len(exc_info.value.errors) == 1
        assert "section_2" in exc_info.value.section_gids

    @pytest.mark.asyncio
    async def test_fetch_gids_respects_semaphore(self) -> None:
        """Test GID enumeration respects concurrency limit."""
        many_sections = [
            Section(gid=f"section_{i}", name=f"Section {i}") for i in range(15)
        ]
        sections_client = create_mock_sections_client(many_sections)

        # Track concurrent requests
        concurrent_count = 0
        max_concurrent_observed = 0
        lock = asyncio.Lock()

        async def track_concurrency_collect():
            nonlocal concurrent_count, max_concurrent_observed
            async with lock:
                concurrent_count += 1
                if concurrent_count > max_concurrent_observed:
                    max_concurrent_observed = concurrent_count

            await asyncio.sleep(0.01)

            async with lock:
                concurrent_count -= 1

            return []

        def create_tracking_iterator(
            section: str | None = None, **kwargs: Any
        ) -> MagicMock:
            mock_iterator = MagicMock()
            mock_iterator.collect = track_concurrency_collect
            return mock_iterator

        tasks_client = MagicMock()
        tasks_client.list_async = MagicMock(side_effect=create_tracking_iterator)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
            max_concurrent=4,
        )

        await fetcher.fetch_section_task_gids_async()

        assert max_concurrent_observed <= 4


# =============================================================================
# TestFetchByGids (TDD-CACHE-OPT-P2)
# =============================================================================


class TestFetchByGids:
    """Tests for ParallelSectionFetcher.fetch_by_gids().

    Per TDD-CACHE-OPTIMIZATION-P2 Phase 2: Targeted fetch for cache misses.
    """

    @pytest.mark.asyncio
    async def test_fetch_by_gids_success_with_section_map(
        self,
        mock_tasks_by_section: dict[str, list[Task]],
    ) -> None:
        """Test fetch_by_gids returns only specified GIDs when section map provided."""
        sections = [
            Section(gid="section_1", name="Section 1"),
            Section(gid="section_2", name="Section 2"),
        ]
        sections_client = create_mock_sections_client(sections)
        tasks_client = create_mock_tasks_client(mock_tasks_by_section)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
        )

        # Create section GID map
        section_gid_map = {
            "section_1": ["task_1", "task_2"],
            "section_2": ["task_3"],
        }

        # Fetch only task_2 and task_3
        result = await fetcher.fetch_by_gids(["task_2", "task_3"], section_gid_map)

        assert len(result.tasks) == 2
        gids = {t.gid for t in result.tasks}
        assert gids == {"task_2", "task_3"}

    @pytest.mark.asyncio
    async def test_fetch_by_gids_only_fetches_relevant_sections(
        self,
        mock_tasks_by_section: dict[str, list[Task]],
    ) -> None:
        """Test fetch_by_gids only queries sections containing target GIDs."""
        sections = [
            Section(gid="section_1", name="Section 1"),
            Section(gid="section_2", name="Section 2"),
            Section(gid="section_3", name="Section 3"),
        ]
        sections_client = create_mock_sections_client(sections)
        tasks_client = create_mock_tasks_client(mock_tasks_by_section)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
        )

        section_gid_map = {
            "section_1": ["task_1", "task_2"],
            "section_2": ["task_3"],
            "section_3": [],  # Empty section
        }

        # Fetch only from section_2 (task_3)
        result = await fetcher.fetch_by_gids(["task_3"], section_gid_map)

        # Should only have fetched from section_2
        assert result.sections_fetched == 1
        assert len(result.tasks) == 1
        assert result.tasks[0].gid == "task_3"

    @pytest.mark.asyncio
    async def test_fetch_by_gids_without_section_map(
        self,
        mock_sections: list[Section],
        mock_tasks_by_section: dict[str, list[Task]],
    ) -> None:
        """Test fetch_by_gids enumerates sections when no map provided."""
        sections_client = create_mock_sections_client(mock_sections)
        tasks_client = create_mock_tasks_client(mock_tasks_by_section)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
        )

        # No section map - will enumerate sections first
        result = await fetcher.fetch_by_gids(["task_1", "task_3"], section_gid_map=None)

        # Should have fetched target tasks
        assert len(result.tasks) == 2
        gids = {t.gid for t in result.tasks}
        assert gids == {"task_1", "task_3"}

        # Should have enumerated sections (1 call) plus fetched all sections (3 calls)
        assert result.total_api_calls == 4

    @pytest.mark.asyncio
    async def test_fetch_by_gids_empty_gid_list(self) -> None:
        """Test fetch_by_gids with empty GID list returns empty result."""
        sections_client = create_mock_sections_client([])
        tasks_client = create_mock_tasks_client({})

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
        )

        result = await fetcher.fetch_by_gids([], section_gid_map={})

        assert len(result.tasks) == 0
        assert result.sections_fetched == 0
        assert result.total_api_calls == 0

    @pytest.mark.asyncio
    async def test_fetch_by_gids_deduplicates_multi_homed(
        self,
        multi_homed_tasks: dict[str, list[Task]],
    ) -> None:
        """Test fetch_by_gids deduplicates multi-homed tasks."""
        sections = [
            Section(gid="section_1", name="Section 1"),
            Section(gid="section_2", name="Section 2"),
        ]
        sections_client = create_mock_sections_client(sections)
        tasks_client = create_mock_tasks_client(multi_homed_tasks)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
        )

        section_gid_map = {
            "section_1": ["task_1", "shared_task"],
            "section_2": ["shared_task", "task_2"],
        }

        # Fetch shared_task (present in both sections)
        result = await fetcher.fetch_by_gids(["shared_task"], section_gid_map)

        # Should only have one instance despite appearing in 2 sections
        assert len(result.tasks) == 1
        assert result.tasks[0].gid == "shared_task"

    @pytest.mark.asyncio
    async def test_fetch_by_gids_partial_failure(
        self,
        mock_sections: list[Section],
    ) -> None:
        """Test fetch_by_gids raises ParallelFetchError on section failure."""
        sections_client = create_mock_sections_client(mock_sections)

        tasks_client = MagicMock()

        def create_failing_iterator(
            section: str | None = None, **kwargs: Any
        ) -> MagicMock:
            mock_iterator = MagicMock()
            if section == "section_1":
                mock_iterator.collect = AsyncMock(side_effect=Exception("API Error"))
            else:
                task = Task(
                    gid=f"task_in_{section}",
                    name=f"Task in {section}",
                    resource_subtype="default_task",
                    completed=False,
                    created_at="2024-01-15T10:30:00.000Z",
                    modified_at="2024-01-16T15:45:30.000Z",
                )
                mock_iterator.collect = AsyncMock(return_value=[task])
            return mock_iterator

        tasks_client.list_async = MagicMock(side_effect=create_failing_iterator)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
        )

        section_gid_map = {
            "section_1": ["task_1"],
            "section_2": ["task_2"],
        }

        with pytest.raises(ParallelFetchError) as exc_info:
            await fetcher.fetch_by_gids(["task_1", "task_2"], section_gid_map)

        assert len(exc_info.value.errors) == 1
        assert "section_1" in exc_info.value.section_gids

    @pytest.mark.asyncio
    async def test_fetch_by_gids_filters_to_target_gids(
        self,
        mock_tasks_by_section: dict[str, list[Task]],
    ) -> None:
        """Test fetch_by_gids only returns tasks matching target GIDs."""
        sections = [
            Section(gid="section_1", name="Section 1"),
        ]
        sections_client = create_mock_sections_client(sections)
        tasks_client = create_mock_tasks_client(mock_tasks_by_section)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
        )

        section_gid_map = {
            "section_1": ["task_1", "task_2"],
        }

        # Fetch only task_1 (task_2 should be filtered out)
        result = await fetcher.fetch_by_gids(["task_1"], section_gid_map)

        assert len(result.tasks) == 1
        assert result.tasks[0].gid == "task_1"

    @pytest.mark.asyncio
    async def test_fetch_by_gids_respects_opt_fields(
        self,
        mock_tasks_by_section: dict[str, list[Task]],
    ) -> None:
        """Test fetch_by_gids passes opt_fields to task fetch."""
        sections = [Section(gid="section_1", name="Section 1")]
        sections_client = create_mock_sections_client(sections)
        tasks_client = create_mock_tasks_client(mock_tasks_by_section)

        opt_fields = ["name", "notes", "custom_fields"]

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
            opt_fields=opt_fields,
        )

        section_gid_map = {"section_1": ["task_1"]}
        await fetcher.fetch_by_gids(["task_1"], section_gid_map)

        # Verify opt_fields were passed
        for call in tasks_client.list_async.call_args_list:
            assert call.kwargs.get("opt_fields") == opt_fields

    @pytest.mark.asyncio
    async def test_fetch_by_gids_no_matching_sections(self) -> None:
        """Test fetch_by_gids returns empty when GIDs not in any section."""
        sections_client = create_mock_sections_client([])
        tasks_client = create_mock_tasks_client({})

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
        )

        section_gid_map = {
            "section_1": ["task_1"],
            "section_2": ["task_2"],
        }

        # Request GIDs not in any section
        result = await fetcher.fetch_by_gids(["task_not_found"], section_gid_map)

        assert len(result.tasks) == 0
        assert result.sections_fetched == 0


# =============================================================================
# TestGidEnumerationCache (PRD-CACHE-OPT-P3)
# =============================================================================


class TestGidEnumerationCache:
    """Tests for GID enumeration caching in ParallelSectionFetcher.

    Per PRD-CACHE-OPT-P3 / ADR-0131: Tests for section list caching and
    GID enumeration caching with graceful degradation.
    """

    # -------------------------------------------------------------------------
    # Section List Cache Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_section_list_cache_hit(
        self,
        mock_sections: list[Section],
        mock_tasks_by_section: dict[str, list[Task]],
    ) -> None:
        """Test section list is returned from cache on hit (FR-SECTION-001/002)."""
        from datetime import datetime
        from unittest.mock import MagicMock

        from autom8_asana.cache.entry import CacheEntry, EntryType

        sections_client = create_mock_sections_client(mock_sections)
        tasks_client = create_mock_tasks_client(mock_tasks_by_section)

        # Create mock cache provider with cached sections
        mock_cache = MagicMock()
        cached_entry = CacheEntry(
            key="project:proj123:sections",
            data={
                "sections": [
                    {"gid": "section_1", "name": "Section 1"},
                    {"gid": "section_2", "name": "Section 2"},
                ]
            },
            entry_type=EntryType.PROJECT_SECTIONS,
            version=datetime.now(UTC),
            cached_at=datetime.now(UTC),
            ttl=1800,
        )
        mock_cache.get_versioned = MagicMock(return_value=cached_entry)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
            cache_provider=mock_cache,
        )

        # Call _list_sections directly
        sections = await fetcher._list_sections()

        # Verify cache was checked
        mock_cache.get_versioned.assert_called_once_with(
            "project:proj123:sections", EntryType.PROJECT_SECTIONS
        )

        # Verify API was NOT called (cache hit)
        sections_client.list_for_project_async.assert_not_called()

        # Verify sections from cache
        assert len(sections) == 2
        assert sections[0].gid == "section_1"
        assert sections[1].gid == "section_2"

    @pytest.mark.asyncio
    async def test_section_list_cache_miss_populates(
        self,
        mock_sections: list[Section],
        mock_tasks_by_section: dict[str, list[Task]],
    ) -> None:
        """Test section list cache is populated on miss (FR-SECTION-003)."""
        from unittest.mock import MagicMock

        from autom8_asana.cache.entry import EntryType

        sections_client = create_mock_sections_client(mock_sections)
        tasks_client = create_mock_tasks_client(mock_tasks_by_section)

        # Create mock cache provider (cache miss)
        mock_cache = MagicMock()
        mock_cache.get_versioned = MagicMock(return_value=None)
        mock_cache.set_versioned = MagicMock()

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
            cache_provider=mock_cache,
        )

        # Call _list_sections
        sections = await fetcher._list_sections()

        # Verify API was called (cache miss)
        sections_client.list_for_project_async.assert_called_once_with("proj123")

        # Verify cache was populated
        mock_cache.set_versioned.assert_called_once()
        call_args = mock_cache.set_versioned.call_args
        assert call_args[0][0] == "project:proj123:sections"
        entry = call_args[0][1]
        assert entry.entry_type == EntryType.PROJECT_SECTIONS
        assert entry.ttl == 1800  # 30 minutes
        assert len(entry.data["sections"]) == 3

    @pytest.mark.asyncio
    async def test_section_list_cache_key_format(self) -> None:
        """Test section list cache key format (FR-SECTION-004)."""
        from unittest.mock import MagicMock

        sections_client = MagicMock()
        tasks_client = MagicMock()

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="1234567890",
        )

        key = fetcher._make_cache_key("sections")
        assert key == "project:1234567890:sections"

    # -------------------------------------------------------------------------
    # GID Enumeration Cache Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_gid_enumeration_cache_hit(
        self,
        mock_sections: list[Section],
        mock_tasks_by_section: dict[str, list[Task]],
    ) -> None:
        """Test GID enumeration is returned from cache on hit (FR-GID-001/002)."""
        from datetime import datetime
        from unittest.mock import MagicMock

        from autom8_asana.cache.entry import CacheEntry, EntryType

        sections_client = create_mock_sections_client(mock_sections)
        tasks_client = create_mock_tasks_client(mock_tasks_by_section)

        # Create mock cache provider with cached GID enumeration
        mock_cache = MagicMock()
        cached_entry = CacheEntry(
            key="project:proj123:gid_enumeration",
            data={
                "section_gids": {
                    "section_1": ["task_1", "task_2"],
                    "section_2": ["task_3"],
                    "section_3": [],
                }
            },
            entry_type=EntryType.GID_ENUMERATION,
            version=datetime.now(UTC),
            cached_at=datetime.now(UTC),
            ttl=300,
        )
        mock_cache.get_versioned = MagicMock(return_value=cached_entry)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
            cache_provider=mock_cache,
        )

        # Call fetch_section_task_gids_async
        result = await fetcher.fetch_section_task_gids_async()

        # Verify cache was checked for GID enumeration
        mock_cache.get_versioned.assert_called_once_with(
            "project:proj123:gid_enumeration", EntryType.GID_ENUMERATION
        )

        # Verify API was NOT called (cache hit)
        sections_client.list_for_project_async.assert_not_called()
        tasks_client.list_async.assert_not_called()

        # Verify result from cache
        assert len(result) == 3
        assert result["section_1"] == ["task_1", "task_2"]
        assert result["section_2"] == ["task_3"]
        assert result["section_3"] == []

    @pytest.mark.asyncio
    async def test_gid_enumeration_cache_miss_populates(
        self,
        mock_sections: list[Section],
        mock_tasks_by_section: dict[str, list[Task]],
    ) -> None:
        """Test GID enumeration cache is populated on miss (FR-GID-003)."""
        from datetime import datetime
        from unittest.mock import MagicMock

        from autom8_asana.cache.entry import CacheEntry, EntryType

        sections_client = create_mock_sections_client(mock_sections)
        tasks_client = create_mock_tasks_client(mock_tasks_by_section)

        # Create mock cache provider - GID cache miss, section cache hit
        mock_cache = MagicMock()
        section_cache_entry = CacheEntry(
            key="project:proj123:sections",
            data={
                "sections": [
                    {"gid": "section_1", "name": "Section 1"},
                    {"gid": "section_2", "name": "Section 2"},
                    {"gid": "section_3", "name": "Section 3"},
                ]
            },
            entry_type=EntryType.PROJECT_SECTIONS,
            version=datetime.now(UTC),
            cached_at=datetime.now(UTC),
            ttl=1800,
        )

        def get_versioned_side_effect(key: str, entry_type: EntryType):
            if entry_type == EntryType.GID_ENUMERATION:
                return None  # Cache miss for GID enumeration
            elif entry_type == EntryType.PROJECT_SECTIONS:
                return section_cache_entry  # Cache hit for sections
            return None

        mock_cache.get_versioned = MagicMock(side_effect=get_versioned_side_effect)
        mock_cache.set_versioned = MagicMock()

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
            cache_provider=mock_cache,
        )

        # Call fetch_section_task_gids_async
        result = await fetcher.fetch_section_task_gids_async()

        # Verify GID enumeration cache was populated
        # Find the call that set GID enumeration
        gid_set_calls = [
            call
            for call in mock_cache.set_versioned.call_args_list
            if "gid_enumeration" in str(call)
        ]
        assert len(gid_set_calls) == 1

        entry = gid_set_calls[0][0][1]
        assert entry.entry_type == EntryType.GID_ENUMERATION
        assert entry.ttl == 300  # 5 minutes
        assert "section_gids" in entry.data

    @pytest.mark.asyncio
    async def test_gid_enumeration_cache_key_format(self) -> None:
        """Test GID enumeration cache key format (FR-GID-004)."""
        from unittest.mock import MagicMock

        sections_client = MagicMock()
        tasks_client = MagicMock()

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="1234567890",
        )

        key = fetcher._make_cache_key("gid_enumeration")
        assert key == "project:1234567890:gid_enumeration"

    # -------------------------------------------------------------------------
    # Graceful Degradation Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_cache_failure_graceful_degradation(
        self,
        mock_sections: list[Section],
        mock_tasks_by_section: dict[str, list[Task]],
    ) -> None:
        """Test cache failures don't prevent operation (FR-DEGRADE-001/002)."""
        from unittest.mock import MagicMock

        sections_client = create_mock_sections_client(mock_sections)
        tasks_client = create_mock_tasks_client(mock_tasks_by_section)

        # Create mock cache provider that throws on all operations
        mock_cache = MagicMock()
        mock_cache.get_versioned = MagicMock(side_effect=Exception("Cache unavailable"))
        mock_cache.set_versioned = MagicMock(
            side_effect=Exception("Cache write failed")
        )

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
            cache_provider=mock_cache,
        )

        # Should NOT raise - operation should complete via API
        result = await fetcher.fetch_section_task_gids_async()

        # Verify result is valid (from API, not cache)
        assert len(result) == 3
        assert "section_1" in result
        assert "section_2" in result
        assert "section_3" in result

    @pytest.mark.asyncio
    async def test_cache_provider_none_bypasses_cache(
        self,
        mock_sections: list[Section],
        mock_tasks_by_section: dict[str, list[Task]],
    ) -> None:
        """Test cache_provider=None bypasses caching entirely (FR-DEGRADE-003)."""
        sections_client = create_mock_sections_client(mock_sections)
        tasks_client = create_mock_tasks_client(mock_tasks_by_section)

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
            cache_provider=None,  # No cache provider
        )

        # Should work without cache
        result = await fetcher.fetch_section_task_gids_async()

        # Verify API was called
        sections_client.list_for_project_async.assert_called_once_with("proj123")

        # Verify result is valid
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_cache_errors_logged_as_warnings(
        self,
        mock_sections: list[Section],
        mock_tasks_by_section: dict[str, list[Task]],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test cache errors are logged as warnings (FR-DEGRADE-004)."""
        import logging
        from unittest.mock import MagicMock

        sections_client = create_mock_sections_client(mock_sections)
        tasks_client = create_mock_tasks_client(mock_tasks_by_section)

        # Create mock cache provider that throws
        mock_cache = MagicMock()
        mock_cache.get_versioned = MagicMock(side_effect=Exception("Test error"))
        mock_cache.set_versioned = MagicMock(side_effect=Exception("Write error"))

        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
            cache_provider=mock_cache,
        )

        with caplog.at_level(logging.WARNING):
            await fetcher.fetch_section_task_gids_async()

        # Verify warning was logged
        warning_messages = [
            r.message for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert len(warning_messages) >= 1
        assert any("cache" in msg.lower() for msg in warning_messages)

    # -------------------------------------------------------------------------
    # TTL Constant Tests
    # -------------------------------------------------------------------------

    def test_ttl_constants_defined(self) -> None:
        """Test TTL constants are defined per PRD specification."""
        assert ParallelSectionFetcher._SECTIONS_TTL == 1800  # 30 minutes
        assert ParallelSectionFetcher._GID_ENUM_TTL == 300  # 5 minutes

    # -------------------------------------------------------------------------
    # Backward Compatibility Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_backward_compatible_without_cache_provider(
        self,
        mock_sections: list[Section],
        mock_tasks_by_section: dict[str, list[Task]],
    ) -> None:
        """Test existing code works without cache_provider (backward compat)."""
        sections_client = create_mock_sections_client(mock_sections)
        tasks_client = create_mock_tasks_client(mock_tasks_by_section)

        # Create fetcher WITHOUT cache_provider (existing usage pattern)
        fetcher = ParallelSectionFetcher(
            sections_client=sections_client,
            tasks_client=tasks_client,
            project_gid="proj123",
            max_concurrent=8,
        )

        # All operations should work
        result = await fetcher.fetch_all()
        assert len(result.tasks) == 3

        gid_result = await fetcher.fetch_section_task_gids_async()
        assert len(gid_result) == 3
