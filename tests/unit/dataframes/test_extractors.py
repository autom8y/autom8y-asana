"""Tests for dataframe extractors package.

Per TDD-0009 Phase 3: Comprehensive tests for BaseExtractor, UnitExtractor,
and ContactExtractor covering all field extraction methods.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any

import pytest

from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.extractors.contact import ContactExtractor
from autom8_asana.dataframes.extractors.unit import UnitExtractor
from autom8_asana.dataframes.models.schema import ColumnDef
from autom8_asana.dataframes.models.task_row import ContactRow, TaskRow, UnitRow
from autom8_asana.dataframes.resolver import MockCustomFieldResolver
from autom8_asana.dataframes.schemas.base import BASE_SCHEMA
from autom8_asana.dataframes.schemas.contact import CONTACT_SCHEMA
from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA
from autom8_asana.models.common import NameGid
from autom8_asana.models.task import Task


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


# =============================================================================
# Concrete BaseExtractor for testing abstract methods
# =============================================================================


class ConcreteExtractor(BaseExtractor):
    """Concrete implementation of BaseExtractor for testing."""

    def _create_row(self, data: dict[str, Any]) -> TaskRow:
        """Create TaskRow from extracted data."""
        if data.get("tags") is None:
            data["tags"] = []
        return TaskRow.model_validate(data)


# =============================================================================
# TestBaseExtractor
# =============================================================================


class TestBaseExtractor:
    """Tests for BaseExtractor class."""

    def test_init_with_schema_only(self) -> None:
        """Test extractor initialization with schema only."""
        extractor = ConcreteExtractor(BASE_SCHEMA)

        assert extractor.schema == BASE_SCHEMA
        assert extractor.resolver is None

    def test_init_with_resolver(self, unit_resolver: MockCustomFieldResolver) -> None:
        """Test extractor initialization with resolver."""
        extractor = ConcreteExtractor(BASE_SCHEMA, unit_resolver)

        assert extractor.schema == BASE_SCHEMA
        assert extractor.resolver == unit_resolver

    # -------------------------------------------------------------------------
    # Base field extraction tests
    # -------------------------------------------------------------------------

    def test_extract_gid(self, minimal_task: Task) -> None:
        """Test GID extraction."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        gid = extractor._extract_gid(minimal_task)

        assert gid == "1234567890"

    def test_extract_gid_empty(self) -> None:
        """Test GID extraction with empty value."""
        task = Task(gid="", name="Test")
        extractor = ConcreteExtractor(BASE_SCHEMA)

        gid = extractor._extract_gid(task)
        assert gid == ""

    def test_extract_name(self, minimal_task: Task) -> None:
        """Test name extraction."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        name = extractor._extract_name(minimal_task)

        assert name == "Test Task"

    def test_extract_name_none(self) -> None:
        """Test name extraction with None value."""
        task = Task(gid="123", name=None)
        extractor = ConcreteExtractor(BASE_SCHEMA)

        name = extractor._extract_name(task)
        assert name == ""

    def test_extract_type_from_resource_subtype(self, minimal_task: Task) -> None:
        """Test type extraction from resource_subtype."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        task_type = extractor._extract_type(minimal_task)

        assert task_type == "default_task"

    def test_extract_type_fallback_to_schema(self) -> None:
        """Test type extraction falls back to schema task_type."""
        task = Task(gid="123", name="Test", resource_subtype=None)
        extractor = ConcreteExtractor(BASE_SCHEMA)

        task_type = extractor._extract_type(task)
        assert task_type == "*"  # BASE_SCHEMA.task_type

    def test_extract_created(self, minimal_task: Task) -> None:
        """Test creation datetime extraction."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        created = extractor._extract_created(minimal_task)

        assert isinstance(created, dt.datetime)
        assert created.year == 2024
        assert created.month == 1
        assert created.day == 15
        assert created.hour == 10
        assert created.minute == 30

    def test_extract_created_none(self) -> None:
        """Test creation datetime extraction with None value."""
        task = Task(gid="123", name="Test", created_at=None)
        extractor = ConcreteExtractor(BASE_SCHEMA)

        created = extractor._extract_created(task)
        assert created == dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)

    def test_extract_due_on(self, full_task: Task) -> None:
        """Test due date extraction."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        due_on = extractor._extract_due_on(full_task)

        assert isinstance(due_on, dt.date)
        assert due_on == dt.date(2024, 1, 31)

    def test_extract_due_on_none(self, minimal_task: Task) -> None:
        """Test due date extraction with None value."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        due_on = extractor._extract_due_on(minimal_task)

        assert due_on is None

    def test_extract_is_completed_true(self, full_task: Task) -> None:
        """Test completion status extraction when completed."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        is_completed = extractor._extract_is_completed(full_task)

        assert is_completed is True

    def test_extract_is_completed_false(self, minimal_task: Task) -> None:
        """Test completion status extraction when not completed."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        is_completed = extractor._extract_is_completed(minimal_task)

        assert is_completed is False

    def test_extract_completed_at(self, full_task: Task) -> None:
        """Test completion datetime extraction."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        completed_at = extractor._extract_completed_at(full_task)

        assert isinstance(completed_at, dt.datetime)
        assert completed_at.year == 2024
        assert completed_at.month == 2
        assert completed_at.day == 1

    def test_extract_completed_at_none(self, minimal_task: Task) -> None:
        """Test completion datetime extraction with None value."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        completed_at = extractor._extract_completed_at(minimal_task)

        assert completed_at is None

    def test_extract_url(self, minimal_task: Task) -> None:
        """Test URL construction."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        url = extractor._extract_url(minimal_task)

        assert url == "https://app.asana.com/0/0/1234567890"

    def test_extract_url_empty_gid(self) -> None:
        """Test URL construction with empty GID."""
        task = Task(gid="", name="Test")
        extractor = ConcreteExtractor(BASE_SCHEMA)

        url = extractor._extract_url(task)
        assert url == "https://app.asana.com/0/0/"

    def test_extract_last_modified(self, minimal_task: Task) -> None:
        """Test last modified datetime extraction."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        last_modified = extractor._extract_last_modified(minimal_task)

        assert isinstance(last_modified, dt.datetime)
        assert last_modified.year == 2024
        assert last_modified.month == 1
        assert last_modified.day == 16

    def test_extract_last_modified_none(self) -> None:
        """Test last modified datetime extraction with None value."""
        task = Task(gid="123", name="Test", modified_at=None)
        extractor = ConcreteExtractor(BASE_SCHEMA)

        last_modified = extractor._extract_last_modified(task)
        assert last_modified == dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)

    def test_extract_section(self, full_task: Task) -> None:
        """Test section extraction from memberships."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        section = extractor._extract_section(full_task)

        assert section == "In Progress"

    def test_extract_section_with_project_filter(self, full_task: Task) -> None:
        """Test section extraction with project filter."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        section = extractor._extract_section(full_task, project_gid="proj123")

        assert section == "In Progress"

    def test_extract_section_wrong_project(self, full_task: Task) -> None:
        """Test section extraction with non-matching project filter."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        section = extractor._extract_section(full_task, project_gid="other_project")

        assert section is None

    def test_extract_section_no_memberships(self, minimal_task: Task) -> None:
        """Test section extraction with no memberships."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        section = extractor._extract_section(minimal_task)

        assert section is None

    def test_extract_tags(self, full_task: Task) -> None:
        """Test tag names extraction."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        tags = extractor._extract_tags(full_task)

        assert tags == ["Priority", "Review"]

    def test_extract_tags_none(self, minimal_task: Task) -> None:
        """Test tag extraction with None tags."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        tags = extractor._extract_tags(minimal_task)

        assert tags == []

    def test_extract_date_defaults_to_due_on(self, full_task: Task) -> None:
        """Test date extraction defaults to due_on."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        date = extractor._extract_date(full_task)

        assert date == dt.date(2024, 1, 31)

    # -------------------------------------------------------------------------
    # Datetime parsing tests
    # -------------------------------------------------------------------------

    def test_parse_datetime_with_z(self) -> None:
        """Test parsing datetime with Z suffix."""
        result = BaseExtractor._parse_datetime("2024-01-15T10:30:00.000Z")

        assert isinstance(result, dt.datetime)
        assert result.year == 2024
        assert result.tzinfo is not None

    def test_parse_datetime_with_offset(self) -> None:
        """Test parsing datetime with timezone offset."""
        result = BaseExtractor._parse_datetime("2024-01-15T10:30:00+05:00")

        assert isinstance(result, dt.datetime)
        assert result.year == 2024

    def test_parse_datetime_invalid(self) -> None:
        """Test parsing invalid datetime returns epoch."""
        result = BaseExtractor._parse_datetime("invalid")

        assert result == dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)

    def test_parse_date_valid(self) -> None:
        """Test parsing valid date string."""
        result = BaseExtractor._parse_date("2024-01-15")

        assert result == dt.date(2024, 1, 15)

    def test_parse_date_invalid(self) -> None:
        """Test parsing invalid date returns epoch."""
        result = BaseExtractor._parse_date("invalid")

        assert result == dt.date(1970, 1, 1)

    # -------------------------------------------------------------------------
    # Full extraction tests
    # -------------------------------------------------------------------------

    def test_extract_full_task(self, full_task: Task) -> None:
        """Test full extraction of all base fields."""
        extractor = ConcreteExtractor(BASE_SCHEMA)
        row = extractor.extract(full_task)

        assert isinstance(row, TaskRow)
        assert row.gid == "9876543210"
        assert row.name == "Full Test Task"
        assert row.is_completed is True
        assert row.section == "In Progress"
        assert row.tags == ["Priority", "Review"]
        assert "https://app.asana.com/0/0/9876543210" == row.url

    def test_extract_continues_on_field_error(
        self,
        full_task: Task,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test that extraction continues when individual fields fail.

        Using UnitExtractor which properly handles extra fields in UnitRow.
        Testing with a resolver that doesn't have all custom fields.
        """
        # Create a resolver with some but not all fields
        partial_resolver = MockCustomFieldResolver(
            {
                "mrr": Decimal("5000"),
                # Missing: weekly_ad_spend, products, etc.
            }
        )

        extractor = UnitExtractor(UNIT_SCHEMA, partial_resolver)
        row = extractor.extract(full_task)

        # Should succeed - base fields and available custom fields extracted
        assert row.gid == "9876543210"
        assert row.name == "Full Test Task"
        assert row.mrr == Decimal("5000")
        # Missing fields should be None or empty list
        assert row.weekly_ad_spend is None

    def test_extract_column_raises_when_resolver_missing(
        self,
        minimal_task: Task,
    ) -> None:
        """Test that _extract_column raises ValueError when resolver needed but missing."""
        # Test direct access to _extract_column without error handling wrapper
        extractor = ConcreteExtractor(BASE_SCHEMA, resolver=None)

        col = ColumnDef("custom", "Utf8", nullable=True, source="cf:Custom")

        with pytest.raises(ValueError, match="Resolver required"):
            extractor._extract_column(minimal_task, col)


# =============================================================================
# TestUnitExtractor
# =============================================================================


class TestUnitExtractor:
    """Tests for UnitExtractor class."""

    def test_extract_type_always_unit(
        self,
        minimal_task: Task,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test that type extraction always returns 'Unit'."""
        extractor = UnitExtractor(UNIT_SCHEMA, unit_resolver)
        task_type = extractor._extract_type(minimal_task)

        assert task_type == "Unit"

    def test_extract_creates_unit_row(
        self,
        full_task: Task,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test that extraction creates UnitRow."""
        extractor = UnitExtractor(UNIT_SCHEMA, unit_resolver)
        row = extractor.extract(full_task)

        assert isinstance(row, UnitRow)
        assert row.type == "Unit"

    def test_extract_custom_fields(
        self,
        full_task: Task,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test extraction of Unit custom fields."""
        extractor = UnitExtractor(UNIT_SCHEMA, unit_resolver)
        row = extractor.extract(full_task)

        assert row.mrr == Decimal("5000.00")
        assert row.weekly_ad_spend == Decimal("1500.50")
        assert row.products == ["Product A", "Product B"]
        assert row.languages == ["English", "Spanish"]
        assert row.discount == Decimal("10.5")
        assert row.vertical == "Healthcare"
        assert row.specialty == "Dental"

    def test_derived_field_office_returns_none(
        self,
        minimal_task: Task,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test that office derived field returns None (stub)."""
        extractor = UnitExtractor(UNIT_SCHEMA, unit_resolver)
        office = extractor._extract_office(minimal_task)

        assert office is None

    def test_office_phone_extracted_from_custom_field(
        self,
        full_task: Task,
    ) -> None:
        """Test that office_phone is extracted from custom field."""
        resolver = MockCustomFieldResolver({"office_phone": "555-123-4567"})
        extractor = UnitExtractor(UNIT_SCHEMA, resolver)
        row = extractor.extract(full_task)

        assert row.office_phone == "555-123-4567"

    def test_office_phone_none_when_not_set(
        self,
        minimal_task: Task,
    ) -> None:
        """Test that office_phone returns None when custom field is not set."""
        resolver = MockCustomFieldResolver({})  # No office_phone configured
        extractor = UnitExtractor(UNIT_SCHEMA, resolver)
        row = extractor.extract(minimal_task)

        assert row.office_phone is None

    def test_derived_field_vertical_id_returns_none(
        self,
        minimal_task: Task,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test that vertical_id derived field returns None (stub)."""
        extractor = UnitExtractor(UNIT_SCHEMA, unit_resolver)
        vertical_id = extractor._extract_vertical_id(minimal_task)

        assert vertical_id is None

    def test_derived_field_max_pipeline_stage_returns_none(
        self,
        minimal_task: Task,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test that max_pipeline_stage derived field returns None (stub)."""
        extractor = UnitExtractor(UNIT_SCHEMA, unit_resolver)
        max_pipeline_stage = extractor._extract_max_pipeline_stage(minimal_task)

        assert max_pipeline_stage is None

    def test_unit_row_has_23_fields(
        self,
        full_task: Task,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test that UnitRow has all 23 fields."""
        extractor = UnitExtractor(UNIT_SCHEMA, unit_resolver)
        row = extractor.extract(full_task)

        # Base fields (12)
        assert hasattr(row, "gid")
        assert hasattr(row, "name")
        assert hasattr(row, "type")
        assert hasattr(row, "date")
        assert hasattr(row, "created")
        assert hasattr(row, "due_on")
        assert hasattr(row, "is_completed")
        assert hasattr(row, "completed_at")
        assert hasattr(row, "url")
        assert hasattr(row, "last_modified")
        assert hasattr(row, "section")
        assert hasattr(row, "tags")

        # Unit fields (11)
        assert hasattr(row, "mrr")
        assert hasattr(row, "weekly_ad_spend")
        assert hasattr(row, "products")
        assert hasattr(row, "languages")
        assert hasattr(row, "discount")
        assert hasattr(row, "office")
        assert hasattr(row, "office_phone")
        assert hasattr(row, "vertical")
        assert hasattr(row, "vertical_id")
        assert hasattr(row, "specialty")
        assert hasattr(row, "max_pipeline_stage")

    def test_empty_list_fields_default(
        self,
        minimal_task: Task,
    ) -> None:
        """Test that empty list fields default to empty list."""
        resolver = MockCustomFieldResolver({})  # No values configured
        extractor = UnitExtractor(UNIT_SCHEMA, resolver)
        row = extractor.extract(minimal_task)

        assert row.tags == []
        assert row.products == []
        assert row.languages == []


# =============================================================================
# TestContactExtractor
# =============================================================================


class TestContactExtractor:
    """Tests for ContactExtractor class."""

    def test_extract_type_always_contact(
        self,
        minimal_task: Task,
        contact_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test that type extraction always returns 'Contact'."""
        extractor = ContactExtractor(CONTACT_SCHEMA, contact_resolver)
        task_type = extractor._extract_type(minimal_task)

        assert task_type == "Contact"

    def test_extract_creates_contact_row(
        self,
        full_task: Task,
        contact_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test that extraction creates ContactRow."""
        extractor = ContactExtractor(CONTACT_SCHEMA, contact_resolver)
        row = extractor.extract(full_task)

        assert isinstance(row, ContactRow)
        assert row.type == "Contact"

    def test_extract_custom_fields(
        self,
        full_task: Task,
        contact_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test extraction of Contact custom fields."""
        extractor = ContactExtractor(CONTACT_SCHEMA, contact_resolver)
        row = extractor.extract(full_task)

        assert row.full_name == "John Doe"
        assert row.nickname == "Johnny"
        assert row.contact_phone == "+1-555-0123"
        assert row.contact_email == "john.doe@example.com"
        assert row.position == "Manager"
        assert row.employee_id == "EMP001"
        assert row.contact_url == "https://linkedin.com/in/johndoe"
        assert row.time_zone == "America/New_York"
        assert row.city == "New York"

    def test_contact_row_has_21_fields(
        self,
        full_task: Task,
        contact_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test that ContactRow has all 21 fields."""
        extractor = ContactExtractor(CONTACT_SCHEMA, contact_resolver)
        row = extractor.extract(full_task)

        # Base fields (12)
        assert hasattr(row, "gid")
        assert hasattr(row, "name")
        assert hasattr(row, "type")
        assert hasattr(row, "date")
        assert hasattr(row, "created")
        assert hasattr(row, "due_on")
        assert hasattr(row, "is_completed")
        assert hasattr(row, "completed_at")
        assert hasattr(row, "url")
        assert hasattr(row, "last_modified")
        assert hasattr(row, "section")
        assert hasattr(row, "tags")

        # Contact fields (9)
        assert hasattr(row, "full_name")
        assert hasattr(row, "nickname")
        assert hasattr(row, "contact_phone")
        assert hasattr(row, "contact_email")
        assert hasattr(row, "position")
        assert hasattr(row, "employee_id")
        assert hasattr(row, "contact_url")
        assert hasattr(row, "time_zone")
        assert hasattr(row, "city")

    def test_empty_list_fields_default(
        self,
        minimal_task: Task,
    ) -> None:
        """Test that empty list fields default to empty list."""
        resolver = MockCustomFieldResolver({})  # No values configured
        extractor = ContactExtractor(CONTACT_SCHEMA, resolver)
        row = extractor.extract(minimal_task)

        assert row.tags == []

    def test_missing_contact_fields_are_none(
        self,
        minimal_task: Task,
    ) -> None:
        """Test that missing contact fields return None."""
        resolver = MockCustomFieldResolver({})  # No values configured
        extractor = ContactExtractor(CONTACT_SCHEMA, resolver)
        row = extractor.extract(minimal_task)

        assert row.full_name is None
        assert row.nickname is None
        assert row.contact_phone is None
        assert row.contact_email is None


# =============================================================================
# Integration tests
# =============================================================================


class TestExtractorIntegration:
    """Integration tests for extractor package."""

    def test_unit_extractor_to_dict_for_polars(
        self,
        full_task: Task,
        unit_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test that UnitRow.to_dict() produces Polars-compatible dict."""
        extractor = UnitExtractor(UNIT_SCHEMA, unit_resolver)
        row = extractor.extract(full_task)
        data = row.to_dict()

        # Check types are Polars-compatible
        assert isinstance(data["gid"], str)
        assert isinstance(data["name"], str)
        assert isinstance(data["is_completed"], bool)
        assert isinstance(data["tags"], list)
        # Decimal converted to float for Polars
        assert isinstance(data["mrr"], float)

    def test_contact_extractor_to_dict_for_polars(
        self,
        full_task: Task,
        contact_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test that ContactRow.to_dict() produces Polars-compatible dict."""
        extractor = ContactExtractor(CONTACT_SCHEMA, contact_resolver)
        row = extractor.extract(full_task)
        data = row.to_dict()

        # Check types are Polars-compatible
        assert isinstance(data["gid"], str)
        assert isinstance(data["full_name"], str)
        assert isinstance(data["tags"], list)

    def test_extractors_use_same_base_logic(
        self,
        full_task: Task,
        unit_resolver: MockCustomFieldResolver,
        contact_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test that both extractors produce same base field values."""
        unit_extractor = UnitExtractor(UNIT_SCHEMA, unit_resolver)
        contact_extractor = ContactExtractor(CONTACT_SCHEMA, contact_resolver)

        unit_row = unit_extractor.extract(full_task)
        contact_row = contact_extractor.extract(full_task)

        # Base fields should be identical (except type)
        assert unit_row.gid == contact_row.gid
        assert unit_row.name == contact_row.name
        assert unit_row.created == contact_row.created
        assert unit_row.url == contact_row.url
        assert unit_row.section == contact_row.section
        assert unit_row.tags == contact_row.tags

        # Types should differ
        assert unit_row.type == "Unit"
        assert contact_row.type == "Contact"

    def test_schema_column_count_matches_extractor(
        self,
        full_task: Task,
        unit_resolver: MockCustomFieldResolver,
        contact_resolver: MockCustomFieldResolver,
    ) -> None:
        """Test that schema column counts match expected values."""
        # UNIT_SCHEMA should have 23 columns (12 base + 11 unit)
        assert len(UNIT_SCHEMA.columns) == 23

        # CONTACT_SCHEMA should have 21 columns (12 base + 9 contact)
        assert len(CONTACT_SCHEMA.columns) == 21

        # BASE_SCHEMA should have 12 columns
        assert len(BASE_SCHEMA.columns) == 12
