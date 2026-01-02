"""Validation tests for DataFrame builders.

Per Session 5 Pragmatic Gap Closure: Basic validation tests covering:
1. Small project (< 100 tasks) - eager evaluation
2. Large project (> 100 tasks) - lazy evaluation triggers
3. Mixed task types in same project
4. Custom field extraction with various types
5. Section filtering by name
6. Empty states (empty project, empty section)
7. Builder produces correct schema
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import polars as pl
import pytest

from autom8_asana.dataframes.builders import (
    LAZY_THRESHOLD,
    DataFrameBuilder,
    ProjectDataFrameBuilder,
    SectionDataFrameBuilder,
)
from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.models.schema import DataFrameSchema
from autom8_asana.dataframes.resolver import MockCustomFieldResolver
from autom8_asana.dataframes.schemas import BASE_SCHEMA, CONTACT_SCHEMA, UNIT_SCHEMA
from autom8_asana.models.common import NameGid
from autom8_asana.models.task import Task


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def unit_resolver() -> MockCustomFieldResolver:
    """Create a mock resolver with Unit custom field values."""
    return MockCustomFieldResolver(
        {
            "mrr": Decimal("5000.00"),
            "weekly_ad_spend": Decimal("1500.50"),
            "products": ["Product A", "Product B"],
            "languages": ["English", "Spanish"],
            "discount": Decimal("10.5"),
            "vertical": "Healthcare",
            "specialty": "Dental",
        }
    )


@pytest.fixture
def contact_resolver() -> MockCustomFieldResolver:
    """Create a mock resolver with Contact custom field values."""
    return MockCustomFieldResolver(
        {
            "full_name": "John Doe",
            "nickname": "Johnny",
            "contact_phone": "+1-555-0123",
            "contact_email": "john.doe@example.com",
            "position": "Manager",
            "employee_id": "EMP001",
            "contact_url": "https://linkedin.com/in/johndoe",
            "time_zone": "America/New_York",
            "city": "New York",
        }
    )


@pytest.fixture
def mock_unified_store() -> MagicMock:
    """Create a mock UnifiedTaskStore for Phase 4 mandatory requirement."""
    return MagicMock()


def create_task(
    gid: str,
    name: str,
    section_name: str = "Active",
    project_gid: str = "proj123",
    completed: bool = False,
) -> Task:
    """Helper to create a task with standard defaults."""
    return Task(
        gid=gid,
        name=name,
        resource_subtype="default_task",
        completed=completed,
        completed_at="2024-02-01T12:00:00.000Z" if completed else None,
        created_at="2024-01-15T10:30:00.000Z",
        modified_at="2024-01-16T15:45:30.000Z",
        memberships=[
            {
                "project": {"gid": project_gid, "name": "Test Project"},
                "section": {"gid": f"sec_{section_name.lower()}", "name": section_name},
            }
        ],
    )


def create_task_batch(
    count: int,
    prefix: str = "task",
    section_name: str = "Active",
    project_gid: str = "proj123",
) -> list[Task]:
    """Create a batch of tasks for testing."""
    return [
        create_task(
            gid=f"{prefix}_{i:06d}",
            name=f"Task {i}",
            section_name=section_name,
            project_gid=project_gid,
        )
        for i in range(count)
    ]


# =============================================================================
# Concrete Builder for Testing
# =============================================================================


class ValidationTestBuilder(DataFrameBuilder):
    """Concrete builder for validation testing."""

    def __init__(
        self,
        schema: DataFrameSchema,
        tasks: list[Task] | None = None,
        project_gid: str | None = None,
        task_type: str = "Unit",
        resolver: Any = None,
        lazy_threshold: int = LAZY_THRESHOLD,
    ) -> None:
        super().__init__(schema, resolver, lazy_threshold)
        self._tasks = tasks or []
        self._project_gid_value = project_gid
        self._task_type = task_type

    def get_tasks(self) -> list[Task]:
        return self._tasks

    def _get_project_gid(self) -> str | None:
        return self._project_gid_value

    def _get_extractor(self) -> BaseExtractor:
        return self._create_extractor(self._task_type)


# =============================================================================
# Test 1: Small Project - Eager Evaluation
# =============================================================================


class TestSmallProjectEagerEvaluation:
    """Tests for small projects (< 100 tasks) using eager evaluation."""

    def test_small_project_uses_eager_by_default(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test small projects auto-select eager evaluation."""
        tasks = create_task_batch(50)  # 50 < LAZY_THRESHOLD (100)

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        # Track which build method is called
        eager_called = False
        lazy_called = False

        original_eager = builder._build_eager
        original_lazy = builder._build_lazy

        def mock_eager(tasks: list[Task]) -> pl.DataFrame:
            nonlocal eager_called
            eager_called = True
            return original_eager(tasks)

        def mock_lazy(tasks: list[Task]) -> pl.DataFrame:
            nonlocal lazy_called
            lazy_called = True
            return original_lazy(tasks)

        builder._build_eager = mock_eager  # type: ignore
        builder._build_lazy = mock_lazy  # type: ignore

        df = builder.build()

        assert eager_called is True
        assert lazy_called is False
        assert len(df) == 50

    def test_small_project_schema_correct(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test small project produces DataFrame with correct schema."""
        tasks = create_task_batch(10)

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        assert df.columns == UNIT_SCHEMA.column_names()
        assert len(df) == 10

    def test_boundary_at_threshold(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test exactly at threshold boundary uses eager."""
        tasks = create_task_batch(LAZY_THRESHOLD)  # Exactly 100

        builder = ValidationTestBuilder(
            schema=UNIT_SCHEMA,
            tasks=tasks,
            project_gid="proj123",
            resolver=unit_resolver,
        )

        # 100 tasks should use eager (threshold is >100, not >=100)
        assert builder._should_use_lazy(LAZY_THRESHOLD, None) is False


# =============================================================================
# Test 2: Large Project - Lazy Evaluation
# =============================================================================


class TestLargeProjectLazyEvaluation:
    """Tests for large projects (> 100 tasks) using lazy evaluation."""

    def test_large_project_uses_lazy_by_default(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test large projects auto-select lazy evaluation."""
        tasks = create_task_batch(150)  # 150 > LAZY_THRESHOLD (100)

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        # Track which build method is called
        eager_called = False
        lazy_called = False

        original_eager = builder._build_eager
        original_lazy = builder._build_lazy

        def mock_eager(tasks: list[Task]) -> pl.DataFrame:
            nonlocal eager_called
            eager_called = True
            return original_eager(tasks)

        def mock_lazy(tasks: list[Task]) -> pl.DataFrame:
            nonlocal lazy_called
            lazy_called = True
            return original_lazy(tasks)

        builder._build_eager = mock_eager  # type: ignore
        builder._build_lazy = mock_lazy  # type: ignore

        df = builder.build()

        assert lazy_called is True
        assert eager_called is False
        assert len(df) == 150

    def test_large_project_schema_correct(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test large project produces DataFrame with correct schema."""
        tasks = create_task_batch(200)

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        assert df.columns == UNIT_SCHEMA.column_names()
        assert len(df) == 200

    def test_lazy_and_eager_produce_same_results(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test lazy and eager produce identical results."""
        tasks = create_task_batch(50)

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        # Build with eager
        eager_df = builder.build(lazy=False)

        # Reset builder state
        builder._extractor = None
        builder._resolver_initialized = False

        # Build with lazy
        lazy_df = builder.build(lazy=True)

        # Compare results
        assert eager_df.shape == lazy_df.shape
        assert eager_df.columns == lazy_df.columns

        # Compare row data
        eager_gids = eager_df["gid"].to_list()
        lazy_gids = lazy_df["gid"].to_list()
        assert eager_gids == lazy_gids


# =============================================================================
# Test 3: Mixed Task Types
# =============================================================================


class TestMixedTaskTypes:
    """Tests for handling different task types in same project."""

    def test_unit_type_extraction(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test Unit task type extraction."""
        tasks = create_task_batch(5)

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        assert len(df) == 5
        # Verify Unit-specific columns exist
        assert "mrr" in df.columns
        assert "weekly_ad_spend" in df.columns
        assert "products" in df.columns

    def test_contact_type_extraction(
        self,
        contact_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test Contact task type extraction."""
        tasks = create_task_batch(5)

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Contact",
            schema=CONTACT_SCHEMA,
            resolver=contact_resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        assert len(df) == 5
        # Verify Contact-specific columns exist
        assert "full_name" in df.columns
        assert "contact_email" in df.columns
        assert "contact_phone" in df.columns

    def test_different_schemas_produce_different_columns(
        self,
        unit_resolver: MockCustomFieldResolver,
        contact_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test different schemas produce different column sets."""
        tasks = create_task_batch(3)

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        unit_builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        contact_builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Contact",
            schema=CONTACT_SCHEMA,
            resolver=contact_resolver,
        unified_store=mock_unified_store,
        )

        unit_df = unit_builder.build()
        contact_df = contact_builder.build()

        # Schemas should be different
        assert unit_df.columns != contact_df.columns
        assert len(unit_df.columns) == len(UNIT_SCHEMA.columns)
        assert len(contact_df.columns) == len(CONTACT_SCHEMA.columns)


# =============================================================================
# Test 4: Custom Field Extraction
# =============================================================================


class TestCustomFieldExtraction:
    """Tests for custom field extraction with various types."""

    def test_decimal_field_extraction(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test Decimal custom fields are extracted correctly."""
        tasks = create_task_batch(1)

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        # Verify decimal values from resolver
        assert df["mrr"][0] == Decimal("5000.00")
        assert df["weekly_ad_spend"][0] == Decimal("1500.50")

    def test_list_field_extraction(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test List[Utf8] custom fields are extracted correctly."""
        tasks = create_task_batch(1)

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        # Verify list values from resolver
        assert df["products"][0].to_list() == ["Product A", "Product B"]
        assert df["languages"][0].to_list() == ["English", "Spanish"]

    def test_string_field_extraction(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test string custom fields are extracted correctly."""
        tasks = create_task_batch(1)

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        # Verify string values from resolver
        assert df["vertical"][0] == "Healthcare"
        assert df["specialty"][0] == "Dental"

    def test_null_custom_field_handling(self,
        mock_unified_store: MagicMock,) -> None:
        """Test null custom fields are handled correctly."""
        # Resolver returns None for missing fields
        resolver = MockCustomFieldResolver(
            {
                "mrr": None,
                "products": None,
            }
        )

        tasks = create_task_batch(1)
        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        # Null values should be None in DataFrame
        assert df["mrr"][0] is None


# =============================================================================
# Test 5: Section Filtering
# =============================================================================


class TestSectionFiltering:
    """Tests for section filtering by name."""

    def test_filter_single_section(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test filtering by a single section name."""
        active_tasks = create_task_batch(5, prefix="active", section_name="Active")
        done_tasks = create_task_batch(3, prefix="done", section_name="Done")
        all_tasks = active_tasks + done_tasks

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = all_tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            sections=["Active"],
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        assert len(df) == 5
        # Verify all tasks are from Active section
        for gid in df["gid"].to_list():
            assert "active" in gid

    def test_filter_multiple_sections(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test filtering by multiple section names."""
        active_tasks = create_task_batch(3, prefix="active", section_name="Active")
        review_tasks = create_task_batch(2, prefix="review", section_name="Review")
        done_tasks = create_task_batch(4, prefix="done", section_name="Done")
        all_tasks = active_tasks + review_tasks + done_tasks

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = all_tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            sections=["Active", "Review"],
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        assert len(df) == 5  # 3 Active + 2 Review

        gids = df["gid"].to_list()
        active_count = sum(1 for g in gids if "active" in g)
        review_count = sum(1 for g in gids if "review" in g)
        done_count = sum(1 for g in gids if "done" in g)

        assert active_count == 3
        assert review_count == 2
        assert done_count == 0

    def test_no_section_filter_returns_all(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test no section filter returns all tasks."""
        active_tasks = create_task_batch(3, prefix="active", section_name="Active")
        done_tasks = create_task_batch(2, prefix="done", section_name="Done")
        all_tasks = active_tasks + done_tasks

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = all_tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            sections=None,  # No filter
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        assert len(df) == 5

    def test_section_filter_no_matches(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test section filter with no matches returns empty DataFrame."""
        active_tasks = create_task_batch(5, prefix="active", section_name="Active")

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = active_tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            sections=["Nonexistent"],
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        assert len(df) == 0
        assert df.columns == UNIT_SCHEMA.column_names()


# =============================================================================
# Test 6: Empty States
# =============================================================================


class TestEmptyStates:
    """Tests for empty project and section states."""

    def test_empty_project_returns_empty_dataframe(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test empty project returns empty DataFrame with schema."""
        project = MagicMock()
        project.gid = "proj_empty"
        project.tasks = []

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        assert len(df) == 0
        assert df.columns == UNIT_SCHEMA.column_names()

    def test_empty_section_returns_empty_dataframe(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test empty section returns empty DataFrame with schema."""
        section = MagicMock()
        section.gid = "sec_empty"
        section.tasks = []
        section.project = NameGid(gid="proj123", name="Test Project")

        builder = SectionDataFrameBuilder(
            section=section,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )

        df = builder.build()

        assert len(df) == 0
        assert df.columns == UNIT_SCHEMA.column_names()

    def test_project_with_none_tasks(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test project with None tasks returns empty DataFrame."""
        project = MagicMock()
        project.gid = "proj123"
        project.tasks = None

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        assert len(df) == 0
        assert df.columns == UNIT_SCHEMA.column_names()

    def test_section_with_none_tasks(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test section with None tasks returns empty DataFrame."""
        section = MagicMock()
        section.gid = "sec456"
        section.tasks = None
        section.project = NameGid(gid="proj123", name="Test Project")

        builder = SectionDataFrameBuilder(
            section=section,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )

        df = builder.build()

        assert len(df) == 0
        assert df.columns == UNIT_SCHEMA.column_names()


# =============================================================================
# Test 7: Builder Produces Correct Schema
# =============================================================================


class TestSchemaCorrectness:
    """Tests verifying builder produces correct schema."""

    def test_unit_schema_column_count(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test UNIT_SCHEMA produces correct number of columns."""
        tasks = create_task_batch(1)

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        # UNIT_SCHEMA has 23 columns (12 base + 11 unit-specific)
        assert len(df.columns) == 23

    def test_contact_schema_column_count(
        self,
        contact_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test CONTACT_SCHEMA produces correct number of columns."""
        tasks = create_task_batch(1)

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Contact",
            schema=CONTACT_SCHEMA,
            resolver=contact_resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        # CONTACT_SCHEMA column count
        assert len(df.columns) == len(CONTACT_SCHEMA.columns)

    def test_base_schema_column_count(self) -> None:
        """Test BASE_SCHEMA produces correct number of columns."""
        tasks = create_task_batch(1)

        builder = ValidationTestBuilder(
            schema=BASE_SCHEMA,
            tasks=tasks,
            project_gid="proj123",
            task_type="Unit",
        )

        df = builder.build()

        # BASE_SCHEMA has 12 columns
        assert len(df.columns) == 12

    def test_schema_column_names_match(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test DataFrame columns match schema column names."""
        tasks = create_task_batch(1)

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        assert df.columns == UNIT_SCHEMA.column_names()

    def test_polars_schema_types(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test DataFrame has correct Polars types."""
        tasks = create_task_batch(1)

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        # Check some key column types
        assert df["gid"].dtype == pl.Utf8
        assert df["name"].dtype == pl.Utf8
        assert df["is_completed"].dtype == pl.Boolean
        assert df["tags"].dtype == pl.List(pl.Utf8)

    def test_empty_dataframe_preserves_schema(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test empty DataFrame preserves full schema."""
        project = MagicMock()
        project.gid = "proj_empty"
        project.tasks = []

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        df = builder.build()

        # Empty but with full schema
        assert len(df) == 0
        assert df.columns == UNIT_SCHEMA.column_names()

        # Types should still be correct
        expected_schema = UNIT_SCHEMA.to_polars_schema()
        for col_name, expected_dtype in expected_schema.items():
            assert df[col_name].dtype == expected_dtype


# =============================================================================
# Integration Tests
# =============================================================================


class TestBuilderIntegration:
    """Integration tests for builder functionality."""

    def test_project_and_section_builder_compatibility(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test ProjectDataFrameBuilder and SectionDataFrameBuilder produce compatible output."""
        task = create_task(gid="task123", name="Test Task")

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = [task]

        section = MagicMock()
        section.gid = "sec456"
        section.tasks = [task]
        section.project = NameGid(gid="proj123", name="Test Project")

        project_builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        section_builder = SectionDataFrameBuilder(
            section=section,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )

        project_df = project_builder.build()
        section_df = section_builder.build()

        # Same schema
        assert project_df.columns == section_df.columns
        # Same task data
        assert project_df["gid"][0] == section_df["gid"][0]
        assert project_df["name"][0] == section_df["name"][0]

    def test_custom_lazy_threshold(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test custom lazy threshold is respected."""
        tasks = create_task_batch(60)

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        # Custom threshold of 50
        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
            lazy_threshold=50,
        unified_store=mock_unified_store,
        )

        # 60 tasks should use lazy with threshold of 50
        assert builder._should_use_lazy(60, None) is True

        # But 40 tasks should use eager
        assert builder._should_use_lazy(40, None) is False

    def test_lazy_override(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test lazy parameter override."""
        tasks = create_task_batch(50)  # Below threshold

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        # Force lazy even though below threshold
        lazy_called = False

        original_lazy = builder._build_lazy

        def mock_lazy(tasks: list[Task]) -> pl.DataFrame:
            nonlocal lazy_called
            lazy_called = True
            return original_lazy(tasks)

        builder._build_lazy = mock_lazy  # type: ignore

        builder.build(lazy=True)

        assert lazy_called is True

    def test_eager_override(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test eager parameter override."""
        tasks = create_task_batch(150)  # Above threshold

        project = MagicMock()
        project.gid = "proj123"
        project.tasks = tasks

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        unified_store=mock_unified_store,
        )

        # Force eager even though above threshold
        eager_called = False

        original_eager = builder._build_eager

        def mock_eager(tasks: list[Task]) -> pl.DataFrame:
            nonlocal eager_called
            eager_called = True
            return original_eager(tasks)

        builder._build_eager = mock_eager  # type: ignore

        builder.build(lazy=False)

        assert eager_called is True
