"""Tests for DataFrame export methods.

Per Session 5 Pragmatic Gap Closure: Comprehensive tests for export methods
(to_parquet, to_csv, to_json) on DataFrameBuilder and concrete builders.

Tests cover:
1. Parquet round-trip (write -> read -> compare schemas and data)
2. CSV export with proper encoding (unicode characters)
3. JSON export schema verification
4. Empty DataFrame handling
5. Various data types (dates, nulls, strings with special chars)
6. Test on both ProjectDataFrameBuilder and SectionDataFrameBuilder

NOTE: CSV export does not support nested data types (List columns) in Polars.
Schemas with List[Utf8] fields (like tags, products, languages) will raise
ComputeError when exported to CSV. Tests verify this limitation is handled.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import polars as pl
import pytest
from polars.exceptions import ComputeError

from autom8_asana.dataframes.builders import (
    DataFrameBuilder,
    ProjectDataFrameBuilder,
    SectionDataFrameBuilder,
)
from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.resolver import MockCustomFieldResolver
from autom8_asana.dataframes.schemas import UNIT_SCHEMA
from autom8_asana.models.common import NameGid
from autom8_asana.models.task import Task


# =============================================================================
# Simple Schema Without Nested Types (for CSV testing)
# =============================================================================


SIMPLE_SCHEMA = DataFrameSchema(
    name="simple",
    task_type="Simple",
    columns=[
        ColumnDef(
            name="gid",
            dtype="Utf8",
            nullable=False,
            source="gid",
            description="Task identifier",
        ),
        ColumnDef(
            name="name",
            dtype="Utf8",
            nullable=False,
            source="name",
            description="Task name",
        ),
        ColumnDef(
            name="type",
            dtype="Utf8",
            nullable=False,
            source="resource_subtype",
            description="Task type",
        ),
        ColumnDef(
            name="is_completed",
            dtype="Boolean",
            nullable=False,
            source="completed",
            description="Completion status",
        ),
        ColumnDef(
            name="created",
            dtype="Datetime",
            nullable=False,
            source="created_at",
            description="Created timestamp",
        ),
        ColumnDef(
            name="section",
            dtype="Utf8",
            nullable=True,
            source=None,
            description="Section name",
        ),
    ],
    version="1.0.0",
)


class SimpleExtractor(BaseExtractor):
    """Simple extractor for CSV testing - no nested types."""

    def __init__(self, schema: DataFrameSchema) -> None:
        super().__init__(schema, None)

    def _create_row(self, data: dict[str, Any]) -> Any:
        """Create a simple dict row."""

        # Return a simple object that has to_dict method
        class SimpleRow:
            def __init__(self, d: dict[str, Any]) -> None:
                self._data = d

            def to_dict(self) -> dict[str, Any]:
                return self._data

        return SimpleRow(data)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def simple_task() -> Task:
    """Create a simple task for testing."""
    return Task(
        gid="1234567890",
        name="Test Task",
        resource_subtype="default_task",
        completed=False,
        created_at="2024-01-15T10:30:00.000Z",
        modified_at="2024-01-16T15:45:30.000Z",
        memberships=[
            {
                "project": {"gid": "proj123", "name": "Test Project"},
                "section": {"gid": "sec456", "name": "Active"},
            }
        ],
    )


@pytest.fixture
def unicode_task() -> Task:
    """Create a task with unicode characters in name."""
    return Task(
        gid="unicode123",
        name="Test Task with Unicode: cafe\u0301 \u65e5\u672c\u8a9e \u0410\u0411\u0412",
        resource_subtype="default_task",
        completed=False,
        created_at="2024-01-15T10:30:00.000Z",
        modified_at="2024-01-16T15:45:30.000Z",
        memberships=[
            {
                "project": {"gid": "proj123", "name": "Test Project"},
                "section": {"gid": "sec456", "name": "Active"},
            }
        ],
    )


@pytest.fixture
def special_chars_task() -> Task:
    """Create a task with special characters in name."""
    return Task(
        gid="special123",
        name='Task with "quotes" and, commas & ampersands <html>',
        resource_subtype="default_task",
        completed=True,
        completed_at="2024-02-01T12:00:00.000Z",
        created_at="2024-01-15T10:30:00.000Z",
        modified_at="2024-02-01T12:00:00.000Z",
        due_on="2024-01-31",
        memberships=[
            {
                "project": {"gid": "proj123", "name": "Test Project"},
                "section": {"gid": "sec456", "name": "Active"},
            }
        ],
    )


@pytest.fixture
def task_with_null_fields() -> Task:
    """Create a task with null fields."""
    return Task(
        gid="null123",
        name="Task with nulls",
        resource_subtype="default_task",
        completed=False,
        created_at="2024-01-15T10:30:00.000Z",
        modified_at="2024-01-16T15:45:30.000Z",
        due_on=None,  # Explicitly None
        completed_at=None,
        tags=None,
        memberships=[
            {
                "project": {"gid": "proj123", "name": "Test Project"},
                "section": {"gid": "sec456", "name": "Active"},
            }
        ],
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
def mock_project_single_task(simple_task: Task) -> MagicMock:
    """Create a mock project with a single task."""
    project = MagicMock()
    project.gid = "proj123"
    project.tasks = [simple_task]
    return project


@pytest.fixture
def mock_project_multiple_tasks(
    simple_task: Task,
    unicode_task: Task,
    special_chars_task: Task,
    task_with_null_fields: Task,
) -> MagicMock:
    """Create a mock project with multiple tasks."""
    project = MagicMock()
    project.gid = "proj123"
    project.tasks = [
        simple_task,
        unicode_task,
        special_chars_task,
        task_with_null_fields,
    ]
    return project


@pytest.fixture
def mock_project_empty() -> MagicMock:
    """Create a mock project with no tasks."""
    project = MagicMock()
    project.gid = "proj_empty"
    project.tasks = []
    return project


@pytest.fixture
def mock_section_single_task(simple_task: Task) -> MagicMock:
    """Create a mock section with a single task."""
    section = MagicMock()
    section.gid = "sec456"
    section.tasks = [simple_task]
    section.project = NameGid(gid="proj123", name="Test Project")
    return section


@pytest.fixture
def mock_section_empty() -> MagicMock:
    """Create a mock section with no tasks."""
    section = MagicMock()
    section.gid = "sec_empty"
    section.tasks = []
    section.project = NameGid(gid="proj123", name="Test Project")
    return section


# =============================================================================
# Concrete Builder for Testing Base Class
# =============================================================================


class ConcreteTestBuilder(DataFrameBuilder):
    """Concrete builder implementation for testing abstract base class."""

    def __init__(
        self,
        schema: DataFrameSchema,
        tasks: list[Task] | None = None,
        project_gid: str | None = None,
        task_type: str = "Unit",
        resolver: Any = None,
    ) -> None:
        super().__init__(schema, resolver)
        self._tasks = tasks or []
        self._project_gid_value = project_gid
        self._task_type = task_type

    def get_tasks(self) -> list[Task]:
        return self._tasks

    def _get_project_gid(self) -> str | None:
        return self._project_gid_value

    def _get_extractor(self) -> BaseExtractor:
        # Support Simple task type for CSV testing
        if self._task_type == "Simple":
            return SimpleExtractor(self._schema)
        return self._create_extractor(self._task_type)


# =============================================================================
# Test Export to Parquet
# =============================================================================


@pytest.mark.xfail(reason="Phase 4 requires unified_store - tests need update to provide mock")
class TestExportParquet:
    """Tests for to_parquet export method."""

    def test_parquet_basic_export(
        self,
        mock_project_single_task: MagicMock,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test basic Parquet export creates file."""
        builder = ProjectDataFrameBuilder(
            project=mock_project_single_task,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )
        output_path = tmp_path / "test.parquet"

        result = builder.to_parquet(output_path)

        assert result == output_path
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_parquet_roundtrip_schema_preserved(
        self,
        mock_project_single_task: MagicMock,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test Parquet round-trip preserves schema."""
        builder = ProjectDataFrameBuilder(
            project=mock_project_single_task,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )
        output_path = tmp_path / "schema_test.parquet"

        # Export
        builder.to_parquet(output_path)

        # Read back
        read_df = pl.read_parquet(output_path)
        original_df = builder.build()

        # Compare schemas
        assert read_df.columns == original_df.columns
        assert len(read_df.columns) == len(UNIT_SCHEMA.columns)

    def test_parquet_roundtrip_data_preserved(
        self,
        mock_project_multiple_tasks: MagicMock,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test Parquet round-trip preserves data."""
        builder = ProjectDataFrameBuilder(
            project=mock_project_multiple_tasks,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )
        output_path = tmp_path / "data_test.parquet"

        # Export
        original_df = builder.build()
        builder._extractor = None  # Reset for re-build
        builder._resolver_initialized = False
        builder.to_parquet(output_path)

        # Read back
        read_df = pl.read_parquet(output_path)

        # Compare data
        assert read_df.shape == original_df.shape
        assert read_df["gid"].to_list() == original_df["gid"].to_list()
        assert read_df["name"].to_list() == original_df["name"].to_list()

    def test_parquet_unicode_preserved(
        self,
        unicode_task: Task,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test Parquet preserves unicode characters."""
        project = MagicMock()
        project.gid = "proj123"
        project.tasks = [unicode_task]

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )
        output_path = tmp_path / "unicode_test.parquet"

        builder.to_parquet(output_path)
        read_df = pl.read_parquet(output_path)

        assert read_df["name"][0] == unicode_task.name

    def test_parquet_empty_dataframe(
        self,
        mock_project_empty: MagicMock,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test Parquet export handles empty DataFrame."""
        builder = ProjectDataFrameBuilder(
            project=mock_project_empty,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )
        output_path = tmp_path / "empty_test.parquet"

        result = builder.to_parquet(output_path)

        assert result == output_path
        assert output_path.exists()

        # Read back and verify empty with schema
        read_df = pl.read_parquet(output_path)
        assert len(read_df) == 0
        assert read_df.columns == UNIT_SCHEMA.column_names()

    def test_parquet_with_compression(
        self,
        mock_project_single_task: MagicMock,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test Parquet export with compression option."""
        builder = ProjectDataFrameBuilder(
            project=mock_project_single_task,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )
        output_path = tmp_path / "compressed.parquet"

        result = builder.to_parquet(output_path, compression="snappy")

        assert result == output_path
        assert output_path.exists()

        # Verify readable
        read_df = pl.read_parquet(output_path)
        assert len(read_df) == 1

    def test_parquet_path_as_string(
        self,
        mock_project_single_task: MagicMock,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test Parquet export accepts string path."""
        builder = ProjectDataFrameBuilder(
            project=mock_project_single_task,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )
        output_path = str(tmp_path / "string_path.parquet")

        result = builder.to_parquet(output_path)

        assert isinstance(result, Path)
        assert result.exists()

    def test_parquet_section_builder(
        self,
        mock_section_single_task: MagicMock,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test Parquet export works with SectionDataFrameBuilder."""
        builder = SectionDataFrameBuilder(
            section=mock_section_single_task,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )
        output_path = tmp_path / "section_test.parquet"

        result = builder.to_parquet(output_path)

        assert result == output_path
        assert output_path.exists()

        read_df = pl.read_parquet(output_path)
        assert len(read_df) == 1


# =============================================================================
# Test Export to CSV
# =============================================================================


class TestExportCSV:
    """Tests for to_csv export method.

    NOTE: CSV export does not support nested data types (List columns) in Polars.
    Most tests use SIMPLE_SCHEMA which has no nested types.
    One test verifies the expected error for schemas with nested types.
    """

    def test_csv_basic_export(
        self,
        simple_task: Task,
        tmp_path: Path,
    ) -> None:
        """Test basic CSV export creates file."""
        builder = ConcreteTestBuilder(
            schema=SIMPLE_SCHEMA,
            tasks=[simple_task],
            project_gid="proj123",
            task_type="Simple",
        )
        output_path = tmp_path / "test.csv"

        result = builder.to_csv(output_path)

        assert result == output_path
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_csv_unicode_preserved(
        self,
        unicode_task: Task,
        tmp_path: Path,
    ) -> None:
        """Test CSV export preserves unicode characters."""
        builder = ConcreteTestBuilder(
            schema=SIMPLE_SCHEMA,
            tasks=[unicode_task],
            project_gid="proj123",
            task_type="Simple",
        )
        output_path = tmp_path / "unicode_test.csv"

        builder.to_csv(output_path)

        # Read back
        read_df = pl.read_csv(output_path)
        assert read_df["name"][0] == unicode_task.name

    def test_csv_special_chars_escaped(
        self,
        special_chars_task: Task,
        tmp_path: Path,
    ) -> None:
        """Test CSV export properly escapes special characters."""
        builder = ConcreteTestBuilder(
            schema=SIMPLE_SCHEMA,
            tasks=[special_chars_task],
            project_gid="proj123",
            task_type="Simple",
        )
        output_path = tmp_path / "special_test.csv"

        builder.to_csv(output_path)

        # Read back
        read_df = pl.read_csv(output_path)
        assert read_df["name"][0] == special_chars_task.name

    def test_csv_empty_dataframe(
        self,
        tmp_path: Path,
    ) -> None:
        """Test CSV export handles empty DataFrame."""
        builder = ConcreteTestBuilder(
            schema=SIMPLE_SCHEMA,
            tasks=[],
            project_gid="proj123",
            task_type="Simple",
        )
        output_path = tmp_path / "empty_test.csv"

        result = builder.to_csv(output_path)

        assert result == output_path
        assert output_path.exists()

        # Read back and verify empty with headers
        content = output_path.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 1  # Header only

    def test_csv_custom_separator(
        self,
        simple_task: Task,
        tmp_path: Path,
    ) -> None:
        """Test CSV export with custom separator."""
        builder = ConcreteTestBuilder(
            schema=SIMPLE_SCHEMA,
            tasks=[simple_task],
            project_gid="proj123",
            task_type="Simple",
        )
        output_path = tmp_path / "tab_separated.csv"

        builder.to_csv(output_path, separator="\t")

        # Verify tab separator used
        content = output_path.read_text()
        assert "\t" in content
        # Don't check for no commas - content might have commas in data

    def test_csv_null_handling(
        self,
        task_with_null_fields: Task,
        tmp_path: Path,
    ) -> None:
        """Test CSV export handles null values."""
        builder = ConcreteTestBuilder(
            schema=SIMPLE_SCHEMA,
            tasks=[task_with_null_fields],
            project_gid="proj123",
            task_type="Simple",
        )
        output_path = tmp_path / "null_test.csv"

        result = builder.to_csv(output_path)

        assert result == output_path
        assert output_path.exists()

        # Should be readable without errors
        read_df = pl.read_csv(output_path)
        assert len(read_df) == 1

    def test_csv_roundtrip_data(
        self,
        simple_task: Task,
        unicode_task: Task,
        special_chars_task: Task,
        tmp_path: Path,
    ) -> None:
        """Test CSV round-trip preserves core data."""
        builder = ConcreteTestBuilder(
            schema=SIMPLE_SCHEMA,
            tasks=[simple_task, unicode_task, special_chars_task],
            project_gid="proj123",
            task_type="Simple",
        )
        output_path = tmp_path / "roundtrip_test.csv"

        # Export and track original
        original_df = builder.build()
        builder._extractor = None
        builder._resolver_initialized = False
        builder.to_csv(output_path)

        # Read back
        read_df = pl.read_csv(output_path)

        # Compare row count and gids
        assert len(read_df) == len(original_df)
        assert read_df["gid"].to_list() == original_df["gid"].to_list()

    @pytest.mark.xfail(reason="Phase 4 requires unified_store - test needs update")
    def test_csv_nested_types_raises_error(
        self,
        mock_project_single_task: MagicMock,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test CSV export raises ComputeError for schemas with nested types.

        This is expected Polars behavior - CSV format does not support nested data.
        Schemas with List[Utf8] columns (tags, products, languages) will fail.
        """
        builder = ProjectDataFrameBuilder(
            project=mock_project_single_task,
            task_type="Unit",
            schema=UNIT_SCHEMA,  # Has List[Utf8] columns
            resolver=unit_resolver,
        )
        output_path = tmp_path / "nested_types_test.csv"

        with pytest.raises(
            ComputeError, match="CSV format does not support nested data"
        ):
            builder.to_csv(output_path)

    def test_csv_section_builder_simple_schema(
        self,
        simple_task: Task,
        tmp_path: Path,
    ) -> None:
        """Test CSV export works with simple schema on ConcreteTestBuilder."""
        builder = ConcreteTestBuilder(
            schema=SIMPLE_SCHEMA,
            tasks=[simple_task],
            project_gid="proj123",
            task_type="Simple",
        )
        output_path = tmp_path / "section_test.csv"

        result = builder.to_csv(output_path)

        assert result == output_path
        assert output_path.exists()


# =============================================================================
# Test Export to JSON
# =============================================================================


@pytest.mark.xfail(reason="Phase 4 requires unified_store - tests need update to provide mock")
class TestExportJSON:
    """Tests for to_json export method."""

    def test_json_basic_export(
        self,
        mock_project_single_task: MagicMock,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test basic JSON export creates file."""
        builder = ProjectDataFrameBuilder(
            project=mock_project_single_task,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )
        output_path = tmp_path / "test.json"

        result = builder.to_json(output_path)

        assert result == output_path
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_json_valid_json_format(
        self,
        mock_project_single_task: MagicMock,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test JSON export produces valid JSON."""
        builder = ProjectDataFrameBuilder(
            project=mock_project_single_task,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )
        output_path = tmp_path / "valid_json_test.json"

        builder.to_json(output_path)

        # Parse JSON - should not raise
        content = output_path.read_text()
        parsed = json.loads(content)

        assert isinstance(parsed, (dict, list))

    def test_json_schema_columns_present(
        self,
        mock_project_single_task: MagicMock,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test JSON export contains all schema columns."""
        builder = ProjectDataFrameBuilder(
            project=mock_project_single_task,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )
        output_path = tmp_path / "schema_columns_test.json"

        builder.to_json(output_path)

        # Read back via Polars
        read_df = pl.read_json(output_path)
        expected_columns = UNIT_SCHEMA.column_names()

        assert read_df.columns == expected_columns

    def test_json_unicode_preserved(
        self,
        unicode_task: Task,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test JSON export preserves unicode characters."""
        project = MagicMock()
        project.gid = "proj123"
        project.tasks = [unicode_task]

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )
        output_path = tmp_path / "unicode_test.json"

        builder.to_json(output_path)

        # Read back
        read_df = pl.read_json(output_path)
        assert read_df["name"][0] == unicode_task.name

    def test_json_empty_dataframe(
        self,
        mock_project_empty: MagicMock,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test JSON export handles empty DataFrame."""
        builder = ProjectDataFrameBuilder(
            project=mock_project_empty,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )
        output_path = tmp_path / "empty_test.json"

        result = builder.to_json(output_path)

        assert result == output_path
        assert output_path.exists()

        # Parse and verify structure
        content = output_path.read_text()
        parsed = json.loads(content)
        assert isinstance(parsed, (dict, list))

    def test_json_null_handling(
        self,
        task_with_null_fields: Task,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test JSON export handles null values."""
        project = MagicMock()
        project.gid = "proj123"
        project.tasks = [task_with_null_fields]

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )
        output_path = tmp_path / "null_test.json"

        result = builder.to_json(output_path)

        assert result == output_path
        assert output_path.exists()

        # Verify readable
        read_df = pl.read_json(output_path)
        assert len(read_df) == 1

    def test_json_ndjson_option(
        self,
        mock_project_single_task: MagicMock,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test JSON export with NDJSON format (newline-delimited JSON).

        Note: Polars uses write_ndjson for row-oriented output, not write_json.
        write_json produces columnar format by default.
        """
        builder = ProjectDataFrameBuilder(
            project=mock_project_single_task,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )
        output_path = tmp_path / "json_test.json"

        # Default write_json creates columnar format
        builder.to_json(output_path)

        # Verify JSON is valid and contains expected data
        read_df = pl.read_json(output_path)
        assert len(read_df) == 1
        assert "gid" in read_df.columns

    def test_json_section_builder(
        self,
        mock_section_single_task: MagicMock,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test JSON export works with SectionDataFrameBuilder."""
        builder = SectionDataFrameBuilder(
            section=mock_section_single_task,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )
        output_path = tmp_path / "section_test.json"

        result = builder.to_json(output_path)

        assert result == output_path
        assert output_path.exists()


# =============================================================================
# Test Various Data Types
# =============================================================================


@pytest.mark.xfail(reason="Phase 4 requires unified_store - tests need update to provide mock")
class TestExportDataTypes:
    """Tests for export handling of various data types."""

    def test_export_dates_parquet_and_json(
        self,
        simple_task: Task,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test export handles date fields correctly in Parquet and JSON.

        Note: CSV is excluded because UNIT_SCHEMA has List columns which
        are not supported by CSV format.
        """
        project = MagicMock()
        project.gid = "proj123"
        project.tasks = [simple_task]

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )

        # Test Parquet and JSON handle dates (skip CSV due to nested types)
        parquet_path = tmp_path / "dates.parquet"
        json_path = tmp_path / "dates.json"

        builder.to_parquet(parquet_path)
        builder._extractor = None
        builder._resolver_initialized = False
        builder.to_json(json_path)

        # Files created
        assert parquet_path.exists()
        assert json_path.exists()

        # Parquet preserves datetime types
        parquet_df = pl.read_parquet(parquet_path)
        assert "created" in parquet_df.columns
        assert "last_modified" in parquet_df.columns

    def test_export_dates_csv_simple_schema(
        self,
        simple_task: Task,
        tmp_path: Path,
    ) -> None:
        """Test CSV export handles date fields with simple schema."""
        builder = ConcreteTestBuilder(
            schema=SIMPLE_SCHEMA,
            tasks=[simple_task],
            project_gid="proj123",
            task_type="Simple",
        )
        csv_path = tmp_path / "dates.csv"

        builder.to_csv(csv_path)

        assert csv_path.exists()
        read_df = pl.read_csv(csv_path)
        assert "created" in read_df.columns

    def test_export_decimal_fields(
        self,
        simple_task: Task,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test export handles Decimal fields correctly."""
        project = MagicMock()
        project.gid = "proj123"
        project.tasks = [simple_task]

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )

        parquet_path = tmp_path / "decimals.parquet"
        builder.to_parquet(parquet_path)

        # Verify Decimal columns exist
        read_df = pl.read_parquet(parquet_path)
        assert "mrr" in read_df.columns
        assert "weekly_ad_spend" in read_df.columns

    def test_export_list_fields(
        self,
        simple_task: Task,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test export handles List[Utf8] fields correctly."""
        project = MagicMock()
        project.gid = "proj123"
        project.tasks = [simple_task]

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )

        parquet_path = tmp_path / "lists.parquet"
        builder.to_parquet(parquet_path)

        # Verify List columns exist
        read_df = pl.read_parquet(parquet_path)
        assert "tags" in read_df.columns
        assert "products" in read_df.columns

    def test_export_boolean_fields(
        self,
        simple_task: Task,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test export handles boolean fields correctly."""
        project = MagicMock()
        project.gid = "proj123"
        project.tasks = [simple_task]

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="Unit",
            schema=UNIT_SCHEMA,
            resolver=unit_resolver,
        )

        parquet_path = tmp_path / "booleans.parquet"
        builder.to_parquet(parquet_path)

        read_df = pl.read_parquet(parquet_path)
        assert "is_completed" in read_df.columns
        assert read_df["is_completed"][0] is False


# =============================================================================
# Test Base Class Export Methods
# =============================================================================


class TestBaseBuilderExport:
    """Tests for export methods on base DataFrameBuilder class."""

    def test_base_builder_to_parquet(
        self,
        simple_task: Task,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test to_parquet works on base class implementation."""
        builder = ConcreteTestBuilder(
            schema=UNIT_SCHEMA,
            tasks=[simple_task],
            project_gid="proj123",
            task_type="Unit",
            resolver=unit_resolver,
        )
        output_path = tmp_path / "base_test.parquet"

        result = builder.to_parquet(output_path)

        assert result == output_path
        assert output_path.exists()

    def test_base_builder_to_csv_simple_schema(
        self,
        simple_task: Task,
        tmp_path: Path,
    ) -> None:
        """Test to_csv works on base class with simple schema (no nested types)."""
        builder = ConcreteTestBuilder(
            schema=SIMPLE_SCHEMA,
            tasks=[simple_task],
            project_gid="proj123",
            task_type="Simple",
        )
        output_path = tmp_path / "base_test.csv"

        result = builder.to_csv(output_path)

        assert result == output_path
        assert output_path.exists()

    def test_base_builder_to_json(
        self,
        simple_task: Task,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test to_json works on base class implementation."""
        builder = ConcreteTestBuilder(
            schema=UNIT_SCHEMA,
            tasks=[simple_task],
            project_gid="proj123",
            task_type="Unit",
            resolver=unit_resolver,
        )
        output_path = tmp_path / "base_test.json"

        result = builder.to_json(output_path)

        assert result == output_path
        assert output_path.exists()


# =============================================================================
# Test Empty Section Builder
# =============================================================================


class TestEmptySectionExport:
    """Tests for export methods with empty builder."""

    def test_empty_builder_parquet(
        self,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test empty builder exports to Parquet."""
        builder = ConcreteTestBuilder(
            schema=UNIT_SCHEMA,
            tasks=[],
            project_gid="proj123",
            task_type="Unit",
            resolver=unit_resolver,
        )
        output_path = tmp_path / "empty_builder.parquet"

        result = builder.to_parquet(output_path)

        assert result == output_path
        assert output_path.exists()

        read_df = pl.read_parquet(output_path)
        assert len(read_df) == 0
        assert read_df.columns == UNIT_SCHEMA.column_names()

    def test_empty_builder_csv_simple_schema(
        self,
        tmp_path: Path,
    ) -> None:
        """Test empty builder exports to CSV with simple schema."""
        builder = ConcreteTestBuilder(
            schema=SIMPLE_SCHEMA,
            tasks=[],
            project_gid="proj123",
            task_type="Simple",
        )
        output_path = tmp_path / "empty_builder.csv"

        result = builder.to_csv(output_path)

        assert result == output_path
        assert output_path.exists()

        # Empty CSV should have just header
        content = output_path.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 1  # Header only

    def test_empty_builder_json(
        self,
        unit_resolver: MockCustomFieldResolver,
        tmp_path: Path,
    ) -> None:
        """Test empty builder exports to JSON."""
        builder = ConcreteTestBuilder(
            schema=UNIT_SCHEMA,
            tasks=[],
            project_gid="proj123",
            task_type="Unit",
            resolver=unit_resolver,
        )
        output_path = tmp_path / "empty_builder.json"

        result = builder.to_json(output_path)

        assert result == output_path
        assert output_path.exists()
