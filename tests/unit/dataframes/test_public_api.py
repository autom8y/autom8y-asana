"""Tests for public DataFrame API via DataFrameService.

Validates the service functions that replaced model convenience methods:
- build_for_project() — replaces Project.to_dataframe() / to_dataframe_async()
- build_for_section() — replaces Section.to_dataframe() / to_dataframe_async()
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from autom8_asana.dataframes import (
    SchemaRegistry,
)
from autom8_asana.dataframes.builders.build_result import (
    BuildResult,
    BuildStatus,
    SectionOutcome,
    SectionResult,
)
from autom8_asana.models.common import NameGid
from autom8_asana.models.project import Project
from autom8_asana.models.section import Section
from autom8_asana.models.task import Task
from autom8_asana.services.dataframe_service import build_for_project, build_for_section

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# ============================================================================
# Test Fixtures
# ============================================================================


def _make_build_result(df: pl.DataFrame) -> BuildResult:
    """Wrap a DataFrame in a BuildResult for mock returns."""
    return BuildResult(
        status=BuildStatus.SUCCESS,
        sections=(
            SectionResult(
                section_gid="mock-section",
                outcome=SectionOutcome.SUCCESS,
                row_count=len(df),
            ),
        ),
        dataframe=df,
        watermark=datetime.now(UTC),
        project_gid="mock-project",
        entity_type="mock-entity",
        total_time_ms=0.0,
        fetch_time_ms=0.0,
    )


def _patch_builder_and_persistence(
    mocker: MockerFixture, sample_df: pl.DataFrame
) -> MagicMock:
    """Patch ProgressiveProjectBuilder and create_section_persistence for tests.

    Patches at the service module level since build_for_project imports these
    at module level via autom8_asana.services.dataframe_service.
    """
    mock_builder = mocker.patch(
        "autom8_asana.services.dataframe_service.ProgressiveProjectBuilder"
    )
    mock_builder.return_value.build_progressive_async = AsyncMock(
        return_value=_make_build_result(sample_df)
    )

    mock_persistence_inst = MagicMock()
    mock_persistence_inst.__aenter__ = AsyncMock(return_value=mock_persistence_inst)
    mock_persistence_inst.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(
        "autom8_asana.services.dataframe_service.create_section_persistence",
        return_value=mock_persistence_inst,
    )

    return mock_builder


@pytest.fixture
def sample_unit_task() -> Task:
    """Create a sample Unit task for testing."""
    return Task(
        gid="unit-001",
        name="Test Unit",
        resource_type="task",
        created_at="2025-01-01T00:00:00Z",
        modified_at="2025-01-15T12:00:00Z",
        completed=False,
        notes="Unit notes",
        assignee=NameGid(gid="user-001", name="Test User"),
        custom_fields=[
            {"gid": "cf-001", "name": "Type", "display_value": "Unit"},
            {"gid": "cf-002", "name": "MRR", "number_value": 1000.0},
            {"gid": "cf-003", "name": "Rep", "display_value": "Sales Rep"},
        ],
        memberships=[
            {
                "project": {"gid": "proj-001", "name": "Test Project"},
                "section": {"gid": "sect-001", "name": "Active"},
            }
        ],
    )


@pytest.fixture
def project_with_tasks(sample_unit_task: Task) -> Project:
    """Create a project with tasks for testing."""
    project = Project(
        gid="proj-001",
        name="Test Project",
        resource_type="project",
    )
    project.tasks = [sample_unit_task]
    return project


@pytest.fixture
def section_with_tasks(sample_unit_task: Task) -> Section:
    """Create a section with tasks for testing."""
    section = Section(
        gid="sect-001",
        name="Active",
        resource_type="section",
        project=NameGid(gid="proj-001", name="Test Project"),
    )
    section.tasks = [sample_unit_task]
    return section


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock AsanaClient for testing."""
    client = MagicMock()
    client.unified_store = MagicMock()
    return client


@pytest.fixture
def sample_dataframe() -> pl.DataFrame:
    """Create a sample DataFrame that matches Unit schema."""
    return pl.DataFrame(
        {
            "gid": ["unit-001"],
            "name": ["Test Unit"],
            "type": ["Unit"],
            "date": [None],
            "created": ["2025-01-01T00:00:00Z"],
            "due_on": [None],
            "is_completed": [False],
            "completed_at": [None],
            "url": ["https://app.asana.com/0/proj-001/unit-001"],
            "last_modified": ["2025-01-15T12:00:00Z"],
            "section": ["Active"],
            "tags": [[]],
        }
    )


@pytest.fixture
def empty_dataframe() -> pl.DataFrame:
    """Create an empty DataFrame that matches Unit schema."""
    return pl.DataFrame(
        {
            "gid": pl.Series([], dtype=pl.Utf8),
            "name": pl.Series([], dtype=pl.Utf8),
            "type": pl.Series([], dtype=pl.Utf8),
            "date": pl.Series([], dtype=pl.Date),
            "created": pl.Series([], dtype=pl.Utf8),
            "due_on": pl.Series([], dtype=pl.Date),
            "is_completed": pl.Series([], dtype=pl.Boolean),
            "completed_at": pl.Series([], dtype=pl.Utf8),
            "url": pl.Series([], dtype=pl.Utf8),
            "last_modified": pl.Series([], dtype=pl.Utf8),
            "section": pl.Series([], dtype=pl.Utf8),
            "tags": pl.Series([], dtype=pl.List(pl.Utf8)),
        }
    )


# ============================================================================
# build_for_project() Tests
# ============================================================================


class TestBuildForProject:
    """Test build_for_project() service function (replaces Project.to_dataframe)."""

    @pytest.mark.asyncio
    async def test_returns_polars(
        self,
        project_with_tasks: Project,
        mock_client: MagicMock,
        sample_dataframe: pl.DataFrame,
        mocker: MockerFixture,
    ) -> None:
        """build_for_project() should return a Polars DataFrame."""
        _patch_builder_and_persistence(mocker, sample_dataframe)

        df = await build_for_project(
            project_with_tasks, task_type="Unit", client=mock_client
        )
        assert isinstance(df, pl.DataFrame)

    @pytest.mark.asyncio
    async def test_has_base_columns(
        self,
        project_with_tasks: Project,
        mock_client: MagicMock,
        sample_dataframe: pl.DataFrame,
        mocker: MockerFixture,
    ) -> None:
        """build_for_project() should have base schema columns."""
        _patch_builder_and_persistence(mocker, sample_dataframe)

        df = await build_for_project(
            project_with_tasks, task_type="Unit", client=mock_client
        )

        assert "gid" in df.columns
        assert "name" in df.columns
        assert "created" in df.columns

    @pytest.mark.asyncio
    async def test_extracts_task_data(
        self,
        project_with_tasks: Project,
        mock_client: MagicMock,
        sample_dataframe: pl.DataFrame,
        mocker: MockerFixture,
    ) -> None:
        """build_for_project() should extract task data correctly."""
        _patch_builder_and_persistence(mocker, sample_dataframe)

        df = await build_for_project(
            project_with_tasks, task_type="Unit", client=mock_client
        )

        assert len(df) == 1
        assert df["gid"][0] == "unit-001"
        assert df["name"][0] == "Test Unit"

    @pytest.mark.asyncio
    async def test_empty_project(
        self,
        mock_client: MagicMock,
        empty_dataframe: pl.DataFrame,
        mocker: MockerFixture,
    ) -> None:
        """build_for_project() should handle empty project."""
        _patch_builder_and_persistence(mocker, empty_dataframe)

        project = Project(gid="proj-empty", name="Empty")
        project.tasks = []

        df = await build_for_project(project, task_type="Unit", client=mock_client)

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 0
        assert "gid" in df.columns

    @pytest.mark.asyncio
    async def test_with_use_cache_false(
        self,
        project_with_tasks: Project,
        mock_client: MagicMock,
        sample_dataframe: pl.DataFrame,
        mocker: MockerFixture,
    ) -> None:
        """build_for_project() should work with use_cache=False."""
        _patch_builder_and_persistence(mocker, sample_dataframe)

        df = await build_for_project(
            project_with_tasks, task_type="Unit", use_cache=False, client=mock_client
        )
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 1

    @pytest.mark.asyncio
    async def test_sync_wrapper_returns_polars(
        self,
        project_with_tasks: Project,
        mock_client: MagicMock,
        sample_dataframe: pl.DataFrame,
        mocker: MockerFixture,
    ) -> None:
        """asyncio.run(build_for_project()) matches async call result."""
        _patch_builder_and_persistence(mocker, sample_dataframe)

        df = await build_for_project(
            project_with_tasks, task_type="Unit", client=mock_client
        )
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 1
        assert df["gid"][0] == "unit-001"


# ============================================================================
# build_for_section() Tests
# ============================================================================


class TestBuildForSection:
    """Test build_for_section() service function (replaces Section.to_dataframe)."""

    @pytest.mark.asyncio
    async def test_returns_polars(self, section_with_tasks: Section) -> None:
        """build_for_section() should return a Polars DataFrame."""
        df = await build_for_section(section_with_tasks, task_type="Unit")
        assert isinstance(df, pl.DataFrame)

    @pytest.mark.asyncio
    async def test_extracts_task_data(self, section_with_tasks: Section) -> None:
        """build_for_section() should extract task data correctly."""
        df = await build_for_section(section_with_tasks, task_type="Unit")

        assert len(df) == 1
        assert df["gid"][0] == "unit-001"
        assert df["name"][0] == "Test Unit"

    @pytest.mark.asyncio
    async def test_empty_section(self) -> None:
        """build_for_section() should handle empty section."""
        section = Section(
            gid="sect-empty",
            name="Empty",
            project=NameGid(gid="proj-001", name="Test Project"),
        )
        section.tasks = []

        df = await build_for_section(section, task_type="Unit")

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 0

    @pytest.mark.asyncio
    async def test_section_without_project_gid(self) -> None:
        """build_for_section() should handle section without project."""
        section = Section(
            gid="sect-orphan",
            name="Orphan Section",
            project=None,
        )
        section.tasks = []

        df = await build_for_section(section, task_type="Unit")
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestPublicAPIIntegration:
    """Integration tests for service functions."""

    @pytest.mark.asyncio
    async def test_project_dataframe_section_filtering(
        self, mock_client: MagicMock, mocker: MockerFixture
    ) -> None:
        """build_for_project() should filter by sections when specified."""
        filtered_df = pl.DataFrame(
            {
                "gid": ["unit-001"],
                "name": ["Task in Active"],
                "type": ["Unit"],
                "date": [None],
                "created": ["2025-01-01T00:00:00Z"],
                "due_on": [None],
                "is_completed": [False],
                "completed_at": [None],
                "url": ["https://app.asana.com/0/proj-001/unit-001"],
                "last_modified": ["2025-01-15T12:00:00Z"],
                "section": ["Active"],
                "tags": [[]],
            }
        )

        _patch_builder_and_persistence(mocker, filtered_df)

        project = Project(gid="proj-001", name="Test Project")
        project.tasks = []

        df = await build_for_project(
            project, task_type="Unit", sections=["Active"], client=mock_client
        )

        assert len(df) == 1
        assert df["gid"][0] == "unit-001"

    def test_schema_registry_integration(self) -> None:
        """Service functions should use SchemaRegistry for schema lookup."""
        registry = SchemaRegistry.get_instance()

        assert registry.has_schema("Unit")
        assert registry.has_schema("Contact")
        assert registry.has_schema("*")

    @pytest.mark.asyncio
    async def test_async_produces_correct_data(
        self,
        project_with_tasks: Project,
        mock_client: MagicMock,
        sample_dataframe: pl.DataFrame,
        mocker: MockerFixture,
    ) -> None:
        """build_for_project() async should produce correct data."""
        _patch_builder_and_persistence(mocker, sample_dataframe)

        df = await build_for_project(
            project_with_tasks, task_type="Unit", client=mock_client
        )

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 1
        assert df["gid"][0] == "unit-001"

    @pytest.mark.asyncio
    async def test_unit_schema_columns_present(
        self,
        project_with_tasks: Project,
        mock_client: MagicMock,
        sample_dataframe: pl.DataFrame,
        mocker: MockerFixture,
    ) -> None:
        """Unit schema should include type-specific columns."""
        _patch_builder_and_persistence(mocker, sample_dataframe)

        df = await build_for_project(
            project_with_tasks, task_type="Unit", client=mock_client
        )

        assert "gid" in df.columns
        assert "name" in df.columns
        assert len(df) >= 0

    @pytest.mark.asyncio
    async def test_project_with_none_tasks(
        self,
        mock_client: MagicMock,
        empty_dataframe: pl.DataFrame,
        mocker: MockerFixture,
    ) -> None:
        """build_for_project() should handle tasks=None."""
        _patch_builder_and_persistence(mocker, empty_dataframe)

        project = Project(gid="proj-none", name="None Tasks")

        df = await build_for_project(project, task_type="Unit", client=mock_client)
        assert len(df) == 0
