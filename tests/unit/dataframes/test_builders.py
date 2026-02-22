"""Tests for dataframe builders package.

Per TDD-0009 Phase 4: Comprehensive tests for DataFrameBuilder,
ProjectDataFrameBuilder, and SectionDataFrameBuilder covering
lazy/eager evaluation, section filtering, and extractor selection.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import polars as pl
import pytest

from autom8_asana.dataframes.builders import (
    LAZY_THRESHOLD,
    DataFrameBuilder,
)
from autom8_asana.dataframes.resolver import MockCustomFieldResolver
from autom8_asana.dataframes.schemas import BASE_SCHEMA, CONTACT_SCHEMA, UNIT_SCHEMA
from autom8_asana.models.common import NameGid
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.dataframes.extractors.base import BaseExtractor
    from autom8_asana.dataframes.models.schema import DataFrameSchema

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def minimal_task() -> Task:
    """Create a minimal valid Task for testing."""
    return Task(
        gid="1234567890",
        name="Test Task",
        resource_subtype="default_task",
        completed=False,
        created_at="2024-01-15T10:30:00.000Z",
        modified_at="2024-01-16T15:45:30.000Z",
    )


@pytest.fixture
def full_task() -> Task:
    """Create a fully populated Task for testing."""
    return Task(
        gid="9876543210",
        name="Full Test Task",
        resource_subtype="default_task",
        completed=True,
        completed_at="2024-02-01T12:00:00.000Z",
        created_at="2024-01-15T10:30:00.000Z",
        modified_at="2024-02-01T12:00:00.000Z",
        due_on="2024-01-31",
        tags=[
            NameGid(gid="tag1", name="Priority"),
            NameGid(gid="tag2", name="Review"),
        ],
        memberships=[
            {
                "project": {"gid": "proj123", "name": "Test Project"},
                "section": {"gid": "sec456", "name": "In Progress"},
            }
        ],
    )


@pytest.fixture
def task_in_active_section() -> Task:
    """Create a task in the 'Active' section."""
    return Task(
        gid="task_active",
        name="Active Task",
        resource_subtype="default_task",
        completed=False,
        created_at="2024-01-15T10:30:00.000Z",
        modified_at="2024-01-16T15:45:30.000Z",
        memberships=[
            {
                "project": {"gid": "proj123", "name": "Test Project"},
                "section": {"gid": "sec_active", "name": "Active"},
            }
        ],
    )


@pytest.fixture
def task_in_done_section() -> Task:
    """Create a task in the 'Done' section."""
    return Task(
        gid="task_done",
        name="Done Task",
        resource_subtype="default_task",
        completed=True,
        completed_at="2024-02-01T12:00:00.000Z",
        created_at="2024-01-15T10:30:00.000Z",
        modified_at="2024-02-01T12:00:00.000Z",
        memberships=[
            {
                "project": {"gid": "proj123", "name": "Test Project"},
                "section": {"gid": "sec_done", "name": "Done"},
            }
        ],
    )


@pytest.fixture
def task_no_memberships() -> Task:
    """Create a task without memberships."""
    return Task(
        gid="task_no_membership",
        name="No Membership Task",
        resource_subtype="default_task",
        completed=False,
        created_at="2024-01-15T10:30:00.000Z",
        modified_at="2024-01-16T15:45:30.000Z",
        memberships=None,
    )


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
def mock_project(
    full_task: Task,
    task_in_active_section: Task,
    task_in_done_section: Task,
) -> MagicMock:
    """Create a mock Project with tasks."""
    project = MagicMock()
    project.gid = "proj123"
    project.tasks = [full_task, task_in_active_section, task_in_done_section]
    return project


@pytest.fixture
def mock_section(full_task: Task) -> MagicMock:
    """Create a mock Section with tasks."""
    section = MagicMock()
    section.gid = "sec456"
    section.tasks = [full_task]
    section.project = NameGid(gid="proj123", name="Test Project")
    return section


@pytest.fixture
def mock_unified_store() -> MagicMock:
    """Create a mock UnifiedTaskStore for Phase 4 mandatory requirement."""
    return MagicMock()


@pytest.fixture
def many_tasks() -> list[Task]:
    """Create a list of tasks exceeding LAZY_THRESHOLD."""
    tasks = []
    for i in range(LAZY_THRESHOLD + 50):  # 150 tasks
        tasks.append(
            Task(
                gid=f"task_{i:06d}",
                name=f"Task {i}",
                resource_subtype="default_task",
                completed=False,
                created_at="2024-01-15T10:30:00.000Z",
                modified_at="2024-01-16T15:45:30.000Z",
            )
        )
    return tasks


# =============================================================================
# Concrete DataFrameBuilder for testing abstract methods
# =============================================================================


class ConcreteBuilder(DataFrameBuilder):
    """Concrete implementation of DataFrameBuilder for testing."""

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
# TestDataFrameBuilder
# =============================================================================


class TestDataFrameBuilder:
    """Tests for DataFrameBuilder abstract base class."""

    def test_init_with_schema_only(self) -> None:
        """Test builder initialization with schema only."""
        builder = ConcreteBuilder(UNIT_SCHEMA)

        assert builder.schema == UNIT_SCHEMA
        assert builder.resolver is None
        assert builder.lazy_threshold == LAZY_THRESHOLD

    def test_init_with_resolver(self, unit_resolver: MockCustomFieldResolver) -> None:
        """Test builder initialization with resolver."""
        builder = ConcreteBuilder(UNIT_SCHEMA, resolver=unit_resolver)

        assert builder.schema == UNIT_SCHEMA
        assert builder.resolver == unit_resolver

    def test_init_with_custom_lazy_threshold(self) -> None:
        """Test builder initialization with custom lazy threshold."""
        builder = ConcreteBuilder(UNIT_SCHEMA, lazy_threshold=50)

        assert builder.lazy_threshold == 50

    # -------------------------------------------------------------------------
    # Lazy/Eager Selection Tests
    # -------------------------------------------------------------------------

    def test_should_use_lazy_auto_below_threshold(self) -> None:
        """Test auto-select uses eager for small task counts."""
        builder = ConcreteBuilder(UNIT_SCHEMA)

        assert builder._should_use_lazy(50, None) is False
        assert builder._should_use_lazy(100, None) is False

    def test_should_use_lazy_auto_above_threshold(self) -> None:
        """Test auto-select uses lazy for large task counts."""
        builder = ConcreteBuilder(UNIT_SCHEMA)

        assert builder._should_use_lazy(101, None) is True
        assert builder._should_use_lazy(500, None) is True

    def test_should_use_lazy_override_true(self) -> None:
        """Test explicit lazy=True override."""
        builder = ConcreteBuilder(UNIT_SCHEMA)

        assert builder._should_use_lazy(10, True) is True
        assert builder._should_use_lazy(50, True) is True

    def test_should_use_lazy_override_false(self) -> None:
        """Test explicit lazy=False override."""
        builder = ConcreteBuilder(UNIT_SCHEMA)

        assert builder._should_use_lazy(200, False) is False
        assert builder._should_use_lazy(500, False) is False

    def test_should_use_lazy_custom_threshold(self) -> None:
        """Test custom threshold affects auto-selection."""
        builder = ConcreteBuilder(UNIT_SCHEMA, lazy_threshold=50)

        assert builder._should_use_lazy(50, None) is False
        assert builder._should_use_lazy(51, None) is True

    # -------------------------------------------------------------------------
    # Empty DataFrame Tests
    # -------------------------------------------------------------------------

    def test_build_empty_preserves_schema(self) -> None:
        """Test empty DataFrame has correct schema."""
        builder = ConcreteBuilder(UNIT_SCHEMA)
        df = builder._build_empty()

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 0
        assert len(df.columns) == len(UNIT_SCHEMA.columns)
        assert df.columns == UNIT_SCHEMA.column_names()

    def test_build_empty_via_build_method(self) -> None:
        """Test build() returns empty DataFrame when no tasks."""
        builder = ConcreteBuilder(UNIT_SCHEMA, tasks=[])
        df = builder.build()

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 0
        assert df.columns == UNIT_SCHEMA.column_names()

    # -------------------------------------------------------------------------
    # Build Tests
    # -------------------------------------------------------------------------

    def test_build_eager_with_tasks(
        self,
        full_task: Task,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test eager build produces correct DataFrame."""
        builder = ConcreteBuilder(
            UNIT_SCHEMA,
            tasks=[full_task],
            project_gid="proj123",
            task_type="Unit",
            resolver=unit_resolver,
        )
        df = builder.build(lazy=False)

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 1
        assert df["gid"][0] == "9876543210"
        assert df["name"][0] == "Full Test Task"

    def test_build_lazy_with_tasks(
        self,
        full_task: Task,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test lazy build produces correct DataFrame."""
        builder = ConcreteBuilder(
            UNIT_SCHEMA,
            tasks=[full_task],
            project_gid="proj123",
            task_type="Unit",
            resolver=unit_resolver,
        )
        df = builder.build(lazy=True)

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 1
        assert df["gid"][0] == "9876543210"

    def test_build_auto_selects_lazy_for_many_tasks(
        self,
        many_tasks: list[Task],
    ) -> None:
        """Test auto-selection uses lazy for many tasks."""
        # Use BASE_SCHEMA which doesn't require custom fields
        builder = ConcreteBuilder(
            BASE_SCHEMA,
            tasks=many_tasks,
            task_type="Unit",  # Will fail on extractor creation
        )

        # Mock _build_lazy and _build_eager to verify which is called
        build_lazy_called = False
        build_eager_called = False

        original_build_lazy = builder._build_lazy
        original_build_eager = builder._build_eager

        def mock_build_lazy(tasks: list[Task]) -> pl.DataFrame:
            nonlocal build_lazy_called
            build_lazy_called = True
            return pl.DataFrame(schema=BASE_SCHEMA.to_polars_schema())

        def mock_build_eager(tasks: list[Task]) -> pl.DataFrame:
            nonlocal build_eager_called
            build_eager_called = True
            return pl.DataFrame(schema=BASE_SCHEMA.to_polars_schema())

        builder._build_lazy = mock_build_lazy  # type: ignore
        builder._build_eager = mock_build_eager  # type: ignore

        builder.build()

        assert build_lazy_called is True
        assert build_eager_called is False

    def test_build_with_provided_tasks(
        self,
        full_task: Task,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test build() with explicitly provided tasks."""
        builder = ConcreteBuilder(
            UNIT_SCHEMA,
            tasks=[],  # Empty default tasks
            project_gid="proj123",
            task_type="Unit",
            resolver=unit_resolver,
        )
        df = builder.build(tasks=[full_task], lazy=False)

        assert len(df) == 1
        assert df["gid"][0] == "9876543210"

    # -------------------------------------------------------------------------
    # Resolver Lifecycle Tests
    # -------------------------------------------------------------------------

    def test_ensure_resolver_initialized_builds_index(
        self,
        full_task: Task,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test resolver is initialized on first task."""
        # Add custom_fields to task for resolver initialization
        full_task.custom_fields = [
            {"gid": "cf1", "name": "MRR", "number_value": "5000"},
        ]

        builder = ConcreteBuilder(
            UNIT_SCHEMA,
            resolver=unit_resolver,
        )

        assert builder._resolver_initialized is False

        builder._ensure_resolver_initialized(full_task)

        assert builder._resolver_initialized is True

    def test_ensure_resolver_initialized_only_once(
        self,
        full_task: Task,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test resolver initialization is idempotent."""
        full_task.custom_fields = [
            {"gid": "cf1", "name": "MRR", "number_value": "5000"},
        ]

        builder = ConcreteBuilder(
            UNIT_SCHEMA,
            resolver=unit_resolver,
        )

        builder._ensure_resolver_initialized(full_task)
        builder._ensure_resolver_initialized(full_task)  # Second call
        builder._ensure_resolver_initialized(full_task)  # Third call

        # Should still be initialized (idempotent)
        assert builder._resolver_initialized is True

    def test_ensure_resolver_skipped_when_no_resolver(
        self,
        full_task: Task,
    ) -> None:
        """Test resolver initialization is skipped when no resolver."""
        builder = ConcreteBuilder(UNIT_SCHEMA)

        # Should not raise
        builder._ensure_resolver_initialized(full_task)

        assert builder._resolver_initialized is False

    # -------------------------------------------------------------------------
    # Extractor Factory Tests
    # -------------------------------------------------------------------------

    def test_create_extractor_unit(
        self,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test extractor factory creates UnitExtractor."""
        builder = ConcreteBuilder(
            UNIT_SCHEMA,
            task_type="Unit",
            resolver=unit_resolver,
        )
        extractor = builder._get_extractor()

        from autom8_asana.dataframes.extractors import UnitExtractor

        assert isinstance(extractor, UnitExtractor)

    def test_create_extractor_contact(
        self,
        contact_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test extractor factory creates ContactExtractor."""
        builder = ConcreteBuilder(
            CONTACT_SCHEMA,
            task_type="Contact",
            resolver=contact_resolver,
        )
        extractor = builder._get_extractor()

        from autom8_asana.dataframes.extractors import ContactExtractor

        assert isinstance(extractor, ContactExtractor)

    def test_create_extractor_wildcard_type(self) -> None:
        """Test extractor factory creates DefaultExtractor for wildcard type.

        The '*' task_type is used with BASE_SCHEMA for generic task extraction.
        """
        builder = ConcreteBuilder(
            BASE_SCHEMA,
            task_type="*",
        )

        from autom8_asana.dataframes.extractors import DefaultExtractor

        extractor = builder._get_extractor()
        assert isinstance(extractor, DefaultExtractor)

    def test_create_extractor_unknown_type_falls_back_to_default(self) -> None:
        """Test extractor factory falls back to DefaultExtractor for unknown types.

        This matches SchemaRegistry behavior which falls back to BASE_SCHEMA
        for unknown task types.
        """
        builder = ConcreteBuilder(
            BASE_SCHEMA,
            task_type="Unknown",
        )

        from autom8_asana.dataframes.extractors import DefaultExtractor

        extractor = builder._get_extractor()
        assert isinstance(extractor, DefaultExtractor)


# =============================================================================
# TestProjectDataFrameBuilder
# =============================================================================
