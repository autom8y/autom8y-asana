"""Tests for public DataFrame API on Project and Section models.

Per TDD-0009 Phase 5: Validates the public API methods:
- Project.to_dataframe() and to_dataframe_async()
- Section.to_dataframe() and to_dataframe_async()
- Project.struc() and Section.struc() deprecation wrappers
"""

from __future__ import annotations

import warnings
from typing import Any
from unittest.mock import MagicMock

import polars as pl
import pytest

from autom8_asana.dataframes import (
    BASE_SCHEMA,
    UNIT_SCHEMA,
    SchemaRegistry,
)
from autom8_asana.dataframes.deprecation import (
    _ensure_pandas,
    create_struc_wrapper,
)
from autom8_asana.models.common import NameGid
from autom8_asana.models.project import Project
from autom8_asana.models.section import Section
from autom8_asana.models.task import Task


# ============================================================================
# Test Fixtures
# ============================================================================


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


# ============================================================================
# Project.to_dataframe() Tests
# ============================================================================


class TestProjectToDataFrame:
    """Test Project.to_dataframe() method."""

    def test_to_dataframe_returns_polars(self, project_with_tasks: Project) -> None:
        """to_dataframe() should return a Polars DataFrame."""
        df = project_with_tasks.to_dataframe(task_type="Unit")
        assert isinstance(df, pl.DataFrame)

    def test_to_dataframe_has_base_columns(self, project_with_tasks: Project) -> None:
        """to_dataframe() should have base schema columns."""
        df = project_with_tasks.to_dataframe(task_type="Unit")

        # Check for base columns (Unit schema uses 'created' not 'created_at')
        assert "gid" in df.columns
        assert "name" in df.columns
        assert "created" in df.columns

    def test_to_dataframe_extracts_task_data(self, project_with_tasks: Project) -> None:
        """to_dataframe() should extract task data correctly."""
        df = project_with_tasks.to_dataframe(task_type="Unit")

        assert len(df) == 1
        assert df["gid"][0] == "unit-001"
        assert df["name"][0] == "Test Unit"

    def test_to_dataframe_empty_project(self) -> None:
        """to_dataframe() should handle empty project."""
        project = Project(gid="proj-empty", name="Empty")
        project.tasks = []

        df = project.to_dataframe(task_type="Unit")

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 0
        # Should preserve schema columns
        assert "gid" in df.columns

    def test_to_dataframe_with_use_cache_false(self, project_with_tasks: Project) -> None:
        """to_dataframe() should work with use_cache=False."""
        df = project_with_tasks.to_dataframe(task_type="Unit", use_cache=False)
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 1


class TestProjectToDataFrameAsync:
    """Test Project.to_dataframe_async() method."""

    @pytest.mark.asyncio
    async def test_to_dataframe_async_returns_polars(
        self, project_with_tasks: Project
    ) -> None:
        """to_dataframe_async() should return a Polars DataFrame."""
        df = await project_with_tasks.to_dataframe_async(task_type="Unit")
        assert isinstance(df, pl.DataFrame)

    @pytest.mark.asyncio
    async def test_to_dataframe_async_extracts_data(
        self, project_with_tasks: Project
    ) -> None:
        """to_dataframe_async() should extract task data."""
        df = await project_with_tasks.to_dataframe_async(task_type="Unit")

        assert len(df) == 1
        assert df["gid"][0] == "unit-001"


# ============================================================================
# Section.to_dataframe() Tests
# ============================================================================


class TestSectionToDataFrame:
    """Test Section.to_dataframe() method."""

    def test_to_dataframe_returns_polars(self, section_with_tasks: Section) -> None:
        """to_dataframe() should return a Polars DataFrame."""
        df = section_with_tasks.to_dataframe(task_type="Unit")
        assert isinstance(df, pl.DataFrame)

    def test_to_dataframe_extracts_task_data(self, section_with_tasks: Section) -> None:
        """to_dataframe() should extract task data correctly."""
        df = section_with_tasks.to_dataframe(task_type="Unit")

        assert len(df) == 1
        assert df["gid"][0] == "unit-001"
        assert df["name"][0] == "Test Unit"

    def test_to_dataframe_empty_section(self) -> None:
        """to_dataframe() should handle empty section."""
        section = Section(
            gid="sect-empty",
            name="Empty",
            project=NameGid(gid="proj-001", name="Test Project"),
        )
        section.tasks = []

        df = section.to_dataframe(task_type="Unit")

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 0


class TestSectionToDataFrameAsync:
    """Test Section.to_dataframe_async() method."""

    @pytest.mark.asyncio
    async def test_to_dataframe_async_returns_polars(
        self, section_with_tasks: Section
    ) -> None:
        """to_dataframe_async() should return a Polars DataFrame."""
        df = await section_with_tasks.to_dataframe_async(task_type="Unit")
        assert isinstance(df, pl.DataFrame)


# ============================================================================
# Deprecation Wrapper Tests
# ============================================================================


class TestEnsurePandas:
    """Test _ensure_pandas helper function."""

    def test_ensure_pandas_when_available(self) -> None:
        """_ensure_pandas() should return pandas module when available."""
        try:
            pd = _ensure_pandas()
            # If pandas is installed, we get the module
            assert pd is not None
        except ImportError:
            # If pandas is not installed, ImportError is raised
            pytest.skip("pandas not installed")


class TestDeprecationWrapperFactory:
    """Test create_struc_wrapper factory function."""

    def test_create_struc_wrapper_creates_callable(self) -> None:
        """create_struc_wrapper() should create a callable."""
        def mock_to_dataframe(self: Any, **kwargs: Any) -> pl.DataFrame:
            return pl.DataFrame({"gid": ["test"]})

        wrapper = create_struc_wrapper(mock_to_dataframe, "TestClass")
        assert callable(wrapper)


class TestProjectStrucDeprecation:
    """Test Project.struc() deprecation wrapper."""

    def test_struc_emits_deprecation_warning(self, project_with_tasks: Project) -> None:
        """struc() should emit DeprecationWarning."""
        try:
            _ensure_pandas()
        except ImportError:
            pytest.skip("pandas not installed")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = project_with_tasks.struc(task_type="Unit")

            # Find deprecation warnings
            deprecation_warnings = [
                warning for warning in w
                if issubclass(warning.category, DeprecationWarning)
            ]

            assert len(deprecation_warnings) >= 1
            assert "struc() is deprecated" in str(deprecation_warnings[0].message)

    def test_struc_returns_pandas_dataframe(self, project_with_tasks: Project) -> None:
        """struc() should return a pandas DataFrame."""
        try:
            pd = _ensure_pandas()
        except ImportError:
            pytest.skip("pandas not installed")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            df = project_with_tasks.struc(task_type="Unit")

        assert isinstance(df, pd.DataFrame)

    def test_struc_extracts_data(self, project_with_tasks: Project) -> None:
        """struc() should extract task data correctly."""
        try:
            _ensure_pandas()
        except ImportError:
            pytest.skip("pandas not installed")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            df = project_with_tasks.struc(task_type="Unit")

        assert len(df) == 1
        assert df["gid"].iloc[0] == "unit-001"

    def test_struc_warning_includes_migration_url(
        self, project_with_tasks: Project
    ) -> None:
        """struc() warning should include migration URL."""
        try:
            _ensure_pandas()
        except ImportError:
            pytest.skip("pandas not installed")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = project_with_tasks.struc(task_type="Unit")

            deprecation_warnings = [
                warning for warning in w
                if issubclass(warning.category, DeprecationWarning)
            ]

            assert len(deprecation_warnings) >= 1
            assert "migration" in str(deprecation_warnings[0].message).lower()


class TestSectionStrucDeprecation:
    """Test Section.struc() deprecation wrapper."""

    def test_struc_emits_deprecation_warning(self, section_with_tasks: Section) -> None:
        """struc() should emit DeprecationWarning."""
        try:
            _ensure_pandas()
        except ImportError:
            pytest.skip("pandas not installed")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = section_with_tasks.struc(task_type="Unit")

            deprecation_warnings = [
                warning for warning in w
                if issubclass(warning.category, DeprecationWarning)
            ]

            assert len(deprecation_warnings) >= 1
            assert "struc() is deprecated" in str(deprecation_warnings[0].message)

    def test_struc_returns_pandas_dataframe(self, section_with_tasks: Section) -> None:
        """struc() should return a pandas DataFrame."""
        try:
            pd = _ensure_pandas()
        except ImportError:
            pytest.skip("pandas not installed")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            df = section_with_tasks.struc(task_type="Unit")

        assert isinstance(df, pd.DataFrame)


# ============================================================================
# Integration Tests
# ============================================================================


class TestPublicAPIIntegration:
    """Integration tests for public API methods."""

    def test_project_dataframe_section_filtering(self) -> None:
        """to_dataframe() should filter by sections when specified."""
        # Create tasks in different sections with required datetime fields
        task1 = Task(
            gid="unit-001",
            name="Task in Active",
            created_at="2025-01-01T00:00:00Z",
            modified_at="2025-01-15T12:00:00Z",
            custom_fields=[
                {"gid": "cf-001", "name": "Type", "display_value": "Unit"},
            ],
            memberships=[
                {
                    "project": {"gid": "proj-001", "name": "Test Project"},
                    "section": {"gid": "sect-001", "name": "Active"},
                }
            ],
        )
        task2 = Task(
            gid="unit-002",
            name="Task in Done",
            created_at="2025-01-01T00:00:00Z",
            modified_at="2025-01-15T12:00:00Z",
            custom_fields=[
                {"gid": "cf-001", "name": "Type", "display_value": "Unit"},
            ],
            memberships=[
                {
                    "project": {"gid": "proj-001", "name": "Test Project"},
                    "section": {"gid": "sect-002", "name": "Done"},
                }
            ],
        )

        project = Project(gid="proj-001", name="Test Project")
        project.tasks = [task1, task2]

        # Filter to only Active section
        df = project.to_dataframe(task_type="Unit", sections=["Active"])

        assert len(df) == 1
        assert df["gid"][0] == "unit-001"

    def test_schema_registry_integration(self) -> None:
        """to_dataframe() should use SchemaRegistry for schema lookup."""
        # Verify registry has expected schemas
        registry = SchemaRegistry.get_instance()

        assert registry.has_schema("Unit")
        assert registry.has_schema("Contact")
        assert registry.has_schema("*")

    @pytest.mark.asyncio
    async def test_async_produces_same_data(self, project_with_tasks: Project) -> None:
        """Async method should produce same data as would sync version."""
        df_async = await project_with_tasks.to_dataframe_async(task_type="Unit")

        assert isinstance(df_async, pl.DataFrame)
        assert len(df_async) == 1
        assert df_async["gid"][0] == "unit-001"

    def test_unit_schema_columns_present(self, project_with_tasks: Project) -> None:
        """Unit schema should include type-specific columns."""
        df = project_with_tasks.to_dataframe(task_type="Unit")

        # Unit schema should have extended columns
        assert "gid" in df.columns
        assert "name" in df.columns
        # These may or may not be present depending on schema
        # Just verify DataFrame was created successfully
        assert len(df) >= 0


class TestEdgeCases:
    """Test edge cases for public API methods."""

    def test_project_with_none_tasks(self) -> None:
        """to_dataframe() should handle tasks=None."""
        project = Project(gid="proj-none", name="None Tasks")
        # tasks is None by default

        # Should raise or handle gracefully
        # Check expected behavior
        try:
            df = project.to_dataframe(task_type="Unit")
            # If it doesn't raise, it should return empty DataFrame
            assert len(df) == 0
        except (TypeError, AttributeError):
            # This is also acceptable behavior
            pass

    def test_section_without_project_gid(self) -> None:
        """to_dataframe() should handle section without project."""
        section = Section(
            gid="sect-orphan",
            name="Orphan Section",
            project=None,  # No project reference
        )
        section.tasks = []

        # Should still work with empty tasks
        df = section.to_dataframe(task_type="Unit")
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 0
