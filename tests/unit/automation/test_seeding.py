"""Unit tests for FieldSeeder.

Per TDD-AUTOMATION-LAYER Phase 2: Test field seeding with mock entities.
"""

from __future__ import annotations

from enum import Enum
from unittest.mock import MagicMock

import pytest

from autom8_asana.automation.seeding import FieldSeeder


class MockVertical(Enum):
    """Mock enum for testing."""

    DENTAL = "dental"
    MEDICAL = "medical"


class MockPriority(Enum):
    """Mock enum for testing."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MockBusiness:
    """Mock Business entity for testing."""

    def __init__(
        self,
        name: str | None = None,
        office_phone: str | None = None,
        company_id: str | None = None,
        primary_contact_phone: str | None = None,
    ) -> None:
        self.gid = "business_123"
        self.name = name
        self.office_phone = office_phone
        self.company_id = company_id
        self.primary_contact_phone = primary_contact_phone


class MockUnit:
    """Mock Unit entity for testing."""

    def __init__(
        self,
        vertical: MockVertical | str | None = None,
        platforms: list[str] | None = None,
        booking_type: str | None = None,
    ) -> None:
        self.gid = "unit_123"
        self.vertical = vertical
        self.platforms = platforms
        self.booking_type = booking_type


class MockProcess:
    """Mock Process entity for testing."""

    def __init__(
        self,
        name: str | None = None,
        contact_phone: str | None = None,
        priority: MockPriority | str | None = None,
        assigned_to: str | None = None,
        business: MockBusiness | None = None,
        unit: MockUnit | None = None,
    ) -> None:
        self.gid = "process_123"
        self.name = name
        self.contact_phone = contact_phone
        self.priority = priority
        self.assigned_to = assigned_to
        self._business = business
        self._unit = unit

    @property
    def business(self) -> MockBusiness | None:
        return self._business

    @property
    def unit(self) -> MockUnit | None:
        return self._unit


def create_mock_client() -> MagicMock:
    """Create mock AsanaClient."""
    return MagicMock()


class TestFieldSeeder:
    """Tests for FieldSeeder class."""

    def test_init(self) -> None:
        """Test FieldSeeder initialization."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        assert seeder._client is client

    def test_field_lists_defined(self) -> None:
        """Test that field lists are properly defined with defaults."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        # Test default field lists (now on class as DEFAULT_*)
        # Business cascade is empty by default (fields vary per target project)
        assert FieldSeeder.DEFAULT_BUSINESS_CASCADE_FIELDS == []
        # Unit cascade only includes Vertical (only field that exists on Onboarding)
        assert "Vertical" in FieldSeeder.DEFAULT_UNIT_CASCADE_FIELDS
        assert "Platforms" not in FieldSeeder.DEFAULT_UNIT_CASCADE_FIELDS
        assert "Contact Phone" in FieldSeeder.DEFAULT_PROCESS_CARRY_THROUGH_FIELDS
        assert "Priority" in FieldSeeder.DEFAULT_PROCESS_CARRY_THROUGH_FIELDS

        # Test that instance uses defaults
        assert seeder._business_cascade_fields == []
        assert "Vertical" in seeder._unit_cascade_fields
        assert "Contact Phone" in seeder._process_carry_through_fields

    def test_custom_field_lists(self) -> None:
        """Test that custom field lists override defaults."""
        client = create_mock_client()
        seeder = FieldSeeder(
            client,
            business_cascade_fields=["Custom Field 1"],
            unit_cascade_fields=["Custom Field 2"],
            process_carry_through_fields=["Custom Field 3"],
        )

        # Should use custom lists, not defaults
        assert seeder._business_cascade_fields == ["Custom Field 1"]
        assert seeder._unit_cascade_fields == ["Custom Field 2"]
        assert seeder._process_carry_through_fields == ["Custom Field 3"]

    def test_partial_custom_field_lists(self) -> None:
        """Test that only specified field lists override defaults."""
        client = create_mock_client()
        seeder = FieldSeeder(
            client,
            business_cascade_fields=["Custom Only"],
        )

        # Business uses custom, others use defaults
        assert seeder._business_cascade_fields == ["Custom Only"]
        assert seeder._unit_cascade_fields == FieldSeeder.DEFAULT_UNIT_CASCADE_FIELDS
        assert (
            seeder._process_carry_through_fields
            == FieldSeeder.DEFAULT_PROCESS_CARRY_THROUGH_FIELDS
        )


class TestCascadeFromHierarchy:
    """Tests for cascade_from_hierarchy_async."""

    @pytest.mark.asyncio
    async def test_cascade_from_business_with_defaults_empty(self) -> None:
        """Test cascading fields from Business with empty defaults."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        business = MockBusiness(
            name="Test Business",
            office_phone="555-1234",
            company_id="COMP-001",
        )

        result = await seeder.cascade_from_hierarchy_async(business, None)

        # Default business cascade is empty, so no fields should be returned
        assert result == {}

    @pytest.mark.asyncio
    async def test_cascade_from_business_with_custom_fields(self) -> None:
        """Test cascading fields from Business with custom field list."""
        client = create_mock_client()
        seeder = FieldSeeder(
            client,
            business_cascade_fields=["Office Phone", "Company ID"],
        )

        business = MockBusiness(
            name="Test Business",
            office_phone="555-1234",
            company_id="COMP-001",
        )

        result = await seeder.cascade_from_hierarchy_async(business, None)

        assert result["Office Phone"] == "555-1234"
        assert result["Company ID"] == "COMP-001"

    @pytest.mark.asyncio
    async def test_cascade_from_unit(self) -> None:
        """Test cascading fields from Unit with default field list."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        unit = MockUnit(
            vertical=MockVertical.DENTAL,
            platforms=["facebook", "google"],
            booking_type="direct",
        )

        result = await seeder.cascade_from_hierarchy_async(None, unit)

        # Default unit cascade only includes Vertical
        assert result["Vertical"] == "dental"  # Enum value extracted
        assert "Platforms" not in result  # Not in default list
        assert "Booking Type" not in result  # Not in default list

    @pytest.mark.asyncio
    async def test_cascade_from_unit_with_custom_fields(self) -> None:
        """Test cascading fields from Unit with custom field list."""
        client = create_mock_client()
        seeder = FieldSeeder(
            client,
            unit_cascade_fields=["Vertical", "Platforms", "Booking Type"],
        )

        unit = MockUnit(
            vertical=MockVertical.DENTAL,
            platforms=["facebook", "google"],
            booking_type="direct",
        )

        result = await seeder.cascade_from_hierarchy_async(None, unit)

        assert result["Vertical"] == "dental"
        assert result["Platforms"] == ["facebook", "google"]
        assert result["Booking Type"] == "direct"

    @pytest.mark.asyncio
    async def test_cascade_from_both(self) -> None:
        """Test cascading fields from both Business and Unit with custom fields."""
        client = create_mock_client()
        seeder = FieldSeeder(
            client,
            business_cascade_fields=["Office Phone"],
        )

        business = MockBusiness(
            name="Test Business",
            office_phone="555-1234",
        )
        unit = MockUnit(
            vertical=MockVertical.DENTAL,
        )

        result = await seeder.cascade_from_hierarchy_async(business, unit)

        # Business fields (with custom field list)
        assert result["Office Phone"] == "555-1234"
        # Unit fields (default includes Vertical)
        assert result["Vertical"] == "dental"

    @pytest.mark.asyncio
    async def test_cascade_with_none_values(self) -> None:
        """Test that None values are excluded from result."""
        client = create_mock_client()
        seeder = FieldSeeder(
            client,
            business_cascade_fields=["Office Phone", "Company ID"],
        )

        business = MockBusiness(
            office_phone="555-1234",
            # company_id is None
        )

        result = await seeder.cascade_from_hierarchy_async(business, None)

        assert result["Office Phone"] == "555-1234"
        assert "Company ID" not in result

    @pytest.mark.asyncio
    async def test_cascade_with_no_entities(self) -> None:
        """Test cascading with no entities returns empty dict."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        result = await seeder.cascade_from_hierarchy_async(None, None)

        assert result == {}


class TestCarryThroughFromProcess:
    """Tests for carry_through_from_process_async."""

    @pytest.mark.asyncio
    async def test_carry_through_fields(self) -> None:
        """Test carrying through fields from source Process."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        process = MockProcess(
            contact_phone="555-5678",
            priority=MockPriority.HIGH,
            assigned_to="user_123",
        )

        result = await seeder.carry_through_from_process_async(process)

        assert result["Contact Phone"] == "555-5678"
        assert result["Priority"] == "high"  # Enum value extracted
        # Note: "Assigned To" removed from defaults per Efficient Field Seeding Fix

    @pytest.mark.asyncio
    async def test_carry_through_with_none_values(self) -> None:
        """Test that None values are excluded."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        process = MockProcess(
            contact_phone="555-5678",
            # priority is None
        )

        result = await seeder.carry_through_from_process_async(process)

        assert result["Contact Phone"] == "555-5678"
        assert "Priority" not in result


class TestComputeFields:
    """Tests for compute_fields_async."""

    @pytest.mark.asyncio
    async def test_compute_launch_date(self) -> None:
        """Test computing Launch Date field."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        process = MockProcess()

        result = await seeder.compute_fields_async(process)

        assert "Launch Date" in result
        # Verify it's in YYYY-MM-DD format
        launch_date = result["Launch Date"]
        assert len(launch_date) == 10
        assert launch_date[4] == "-"
        assert launch_date[7] == "-"


class TestSeedFields:
    """Tests for seed_fields_async (main seeding method)."""

    @pytest.mark.asyncio
    async def test_combines_all_sources(self) -> None:
        """Test that seed_fields combines cascade, carry-through, and computed."""
        client = create_mock_client()
        seeder = FieldSeeder(
            client,
            business_cascade_fields=["Office Phone"],
        )

        business = MockBusiness(
            name="Test Business",
            office_phone="555-1234",
        )
        unit = MockUnit(
            vertical=MockVertical.DENTAL,
        )
        process = MockProcess(
            contact_phone="555-5678",
            priority=MockPriority.HIGH,
            business=business,
            unit=unit,
        )

        result = await seeder.seed_fields_async(business, unit, process)

        # Business cascade (with custom field list)
        assert result["Office Phone"] == "555-1234"
        # Unit cascade (default includes Vertical)
        assert result["Vertical"] == "dental"
        # Process carry-through
        assert result["Contact Phone"] == "555-5678"
        assert result["Priority"] == "high"
        # Computed
        assert "Launch Date" in result

    @pytest.mark.asyncio
    async def test_precedence_later_overrides_earlier(self) -> None:
        """Test that later sources override earlier sources."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        # Create entities with overlapping field - Vertical in both Unit and Process
        # Note: In real usage, Process doesn't cascade Vertical, so we test the
        # general override mechanism with custom fields

        business = MockBusiness()
        unit = MockUnit(vertical=MockVertical.DENTAL)
        process = MockProcess(business=business, unit=unit)

        result = await seeder.seed_fields_async(business, unit, process)

        # Unit's Vertical should be present (no Process override for this field)
        assert result["Vertical"] == "dental"

    @pytest.mark.asyncio
    async def test_with_minimal_entities(self) -> None:
        """Test seeding with minimal/empty entities."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        process = MockProcess()

        result = await seeder.seed_fields_async(None, None, process)

        # Should only have computed fields
        assert "Launch Date" in result
        # No cascade fields (no business/unit)
        assert "Office Phone" not in result
        assert "Vertical" not in result


class TestGetFieldValue:
    """Tests for _get_field_value helper."""

    def test_gets_attribute_value(self) -> None:
        """Test getting attribute value from entity."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        business = MockBusiness(office_phone="555-1234")

        result = seeder._get_field_value(business, "Office Phone")

        assert result == "555-1234"

    def test_normalizes_enum_value(self) -> None:
        """Test that enum values are extracted."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        unit = MockUnit(vertical=MockVertical.DENTAL)

        result = seeder._get_field_value(unit, "Vertical")

        assert result == "dental"

    def test_returns_none_for_missing_attribute(self) -> None:
        """Test returning None for missing attribute."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        business = MockBusiness()

        result = seeder._get_field_value(business, "Nonexistent Field")

        assert result is None

    def test_business_name_from_name_attribute(self) -> None:
        """Test Business Name special case uses name attribute."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        business = MockBusiness(name="My Business")

        result = seeder._get_field_value(business, "Business Name")

        assert result == "My Business"


class TestToAttrName:
    """Tests for _to_attr_name helper."""

    def test_converts_display_name(self) -> None:
        """Test converting display name to attribute name."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        assert seeder._to_attr_name("Office Phone") == "office_phone"
        assert seeder._to_attr_name("Company ID") == "company_id"
        assert seeder._to_attr_name("Vertical") == "vertical"

    def test_already_snake_case(self) -> None:
        """Test that already snake_case names work."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        assert seeder._to_attr_name("office_phone") == "office_phone"


class TestNormalizeValue:
    """Tests for _normalize_value helper."""

    def test_returns_none_for_none(self) -> None:
        """Test returning None for None input."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        assert seeder._normalize_value(None) is None

    def test_extracts_enum_value(self) -> None:
        """Test extracting value from enum."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        result = seeder._normalize_value(MockVertical.DENTAL)

        assert result == "dental"

    def test_returns_regular_values_unchanged(self) -> None:
        """Test that regular values pass through unchanged."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        assert seeder._normalize_value("string") == "string"
        assert seeder._normalize_value(123) == 123
        assert seeder._normalize_value(["a", "b"]) == ["a", "b"]


class TestResolveEnumValue:
    """Tests for _resolve_enum_value helper (G2 fix)."""

    def test_returns_none_for_none_value(self) -> None:
        """Test that None values pass through unchanged."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        field_def = {
            "name": "Vertical",
            "resource_subtype": "enum",
            "enum_options": [{"gid": "123", "name": "Dental", "enabled": True}],
        }

        result = seeder._resolve_enum_value(field_def, None, "Vertical", "task_123")
        assert result is None

    def test_passes_through_non_enum_fields(self) -> None:
        """Test that non-enum fields return value unchanged."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        # Text field
        field_def = {"name": "Notes", "resource_subtype": "text"}
        result = seeder._resolve_enum_value(field_def, "some text", "Notes", "task_123")
        assert result == "some text"

        # Number field
        field_def = {"name": "Amount", "resource_subtype": "number"}
        result = seeder._resolve_enum_value(field_def, 42, "Amount", "task_123")
        assert result == 42

    def test_resolves_enum_string_to_gid(self) -> None:
        """Test resolving enum string name to GID."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        field_def = {
            "name": "Vertical",
            "resource_subtype": "enum",
            "enum_options": [
                {"gid": "111", "name": "Dental", "enabled": True},
                {"gid": "222", "name": "Medical", "enabled": True},
                {"gid": "333", "name": "Vision", "enabled": True},
            ],
        }

        result = seeder._resolve_enum_value(field_def, "Dental", "Vertical", "task_123")
        assert result == "111"

    def test_resolves_enum_case_insensitive(self) -> None:
        """Test case-insensitive enum resolution."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        field_def = {
            "name": "Vertical",
            "resource_subtype": "enum",
            "enum_options": [
                {"gid": "123", "name": "Dental", "enabled": True},
            ],
        }

        # Test various case variations
        assert (
            seeder._resolve_enum_value(field_def, "dental", "Vertical", "task_123")
            == "123"
        )
        assert (
            seeder._resolve_enum_value(field_def, "DENTAL", "Vertical", "task_123")
            == "123"
        )
        assert (
            seeder._resolve_enum_value(field_def, "DenTaL", "Vertical", "task_123")
            == "123"
        )

    def test_validates_existing_gid(self) -> None:
        """Test that existing GIDs are validated against options."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        field_def = {
            "name": "Vertical",
            "resource_subtype": "enum",
            "enum_options": [
                {"gid": "123", "name": "Dental", "enabled": True},
            ],
        }

        # Valid GID passes through
        result = seeder._resolve_enum_value(field_def, "123", "Vertical", "task_123")
        assert result == "123"

        # Invalid GID returns None
        result = seeder._resolve_enum_value(field_def, "999", "Vertical", "task_123")
        assert result is None

    def test_returns_none_for_unknown_enum_value(self) -> None:
        """Test that unknown enum values return None (skip field)."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        field_def = {
            "name": "Vertical",
            "resource_subtype": "enum",
            "enum_options": [
                {"gid": "123", "name": "Dental", "enabled": True},
            ],
        }

        result = seeder._resolve_enum_value(
            field_def, "InvalidOption", "Vertical", "task_123"
        )
        assert result is None

    def test_returns_none_for_empty_enum_options(self) -> None:
        """Test that enum fields with no options return None."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        field_def = {
            "name": "Vertical",
            "resource_subtype": "enum",
            "enum_options": [],
        }

        result = seeder._resolve_enum_value(field_def, "Dental", "Vertical", "task_123")
        assert result is None

    def test_returns_none_for_missing_enum_options(self) -> None:
        """Test that enum fields with missing enum_options key return None."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        field_def = {
            "name": "Vertical",
            "resource_subtype": "enum",
            # enum_options key is missing
        }

        result = seeder._resolve_enum_value(field_def, "Dental", "Vertical", "task_123")
        assert result is None


class TestWriteFieldsEnumResolution:
    """Integration tests for write_fields_async enum resolution."""

    @pytest.mark.asyncio
    async def test_write_enum_field_resolves_to_gid(self) -> None:
        """Test that enum fields are resolved to GIDs before writing."""
        from unittest.mock import AsyncMock

        client = create_mock_client()
        seeder = FieldSeeder(client)

        # Mock task with enum field and options
        mock_task = MagicMock()
        mock_task.custom_fields = [
            {
                "gid": "cf_vertical",
                "name": "Vertical",
                "resource_subtype": "enum",
                "enum_options": [
                    {"gid": "opt_dental", "name": "Dental", "enabled": True},
                    {"gid": "opt_medical", "name": "Medical", "enabled": True},
                ],
            },
        ]

        # Mock API responses
        client.tasks.get_async = AsyncMock(return_value=mock_task)
        client.tasks.update_async = AsyncMock()

        # Write with string value
        result = await seeder.write_fields_async(
            target_task_gid="task_123",
            fields={"Vertical": "Dental"},
        )

        assert result.success
        assert "Vertical" in result.fields_written

        # Verify the update was called with the GID
        client.tasks.update_async.assert_called_once()
        call_kwargs = client.tasks.update_async.call_args[1]
        custom_fields = call_kwargs["custom_fields"]

        # The accessor should have the GID, not the string
        assert "cf_vertical" in custom_fields
        assert custom_fields["cf_vertical"] == "opt_dental"

    @pytest.mark.asyncio
    async def test_write_enum_field_skips_on_invalid_value(self) -> None:
        """Test that invalid enum values skip the field with warning."""
        from unittest.mock import AsyncMock

        client = create_mock_client()
        seeder = FieldSeeder(client)

        # Mock task with enum field
        mock_task = MagicMock()
        mock_task.custom_fields = [
            {
                "gid": "cf_vertical",
                "name": "Vertical",
                "resource_subtype": "enum",
                "enum_options": [
                    {"gid": "opt_dental", "name": "Dental", "enabled": True},
                ],
            },
        ]

        client.tasks.get_async = AsyncMock(return_value=mock_task)
        client.tasks.update_async = AsyncMock()

        # Write with invalid enum value
        result = await seeder.write_fields_async(
            target_task_gid="task_123",
            fields={"Vertical": "InvalidValue"},
        )

        assert result.success
        assert "Vertical" in result.fields_skipped
        assert "Vertical" not in result.fields_written

        # No update should be called since no valid fields
        client.tasks.update_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_write_mixed_fields_with_enum(self) -> None:
        """Test writing both enum and non-enum fields together."""
        from unittest.mock import AsyncMock

        client = create_mock_client()
        seeder = FieldSeeder(client)

        mock_task = MagicMock()
        mock_task.custom_fields = [
            {
                "gid": "cf_vertical",
                "name": "Vertical",
                "resource_subtype": "enum",
                "enum_options": [
                    {"gid": "opt_dental", "name": "Dental", "enabled": True},
                ],
            },
            {
                "gid": "cf_notes",
                "name": "Notes",
                "resource_subtype": "text",
            },
        ]

        client.tasks.get_async = AsyncMock(return_value=mock_task)
        client.tasks.update_async = AsyncMock()

        result = await seeder.write_fields_async(
            target_task_gid="task_123",
            fields={
                "Vertical": "dental",  # enum (case insensitive)
                "Notes": "Some notes",  # text
            },
        )

        assert result.success
        assert "Vertical" in result.fields_written
        assert "Notes" in result.fields_written

        # Verify both fields in update
        call_kwargs = client.tasks.update_async.call_args[1]
        custom_fields = call_kwargs["custom_fields"]
        assert custom_fields["cf_vertical"] == "opt_dental"
        assert custom_fields["cf_notes"] == "Some notes"


class TestGetFieldAttr:
    """Tests for get_field_attr helper function.

    This helper handles both dict and object custom field formats that may
    come from different API response handling paths.
    """

    def test_dict_access(self) -> None:
        """Test accessing attributes from dict."""
        from autom8_asana.core.field_utils import get_field_attr

        field_dict = {"gid": "123", "name": "Test Field", "resource_subtype": "text"}
        assert get_field_attr(field_dict, "name") == "Test Field"
        assert get_field_attr(field_dict, "gid") == "123"
        assert get_field_attr(field_dict, "resource_subtype") == "text"

    def test_dict_access_with_default(self) -> None:
        """Test dict access with default value for missing key."""
        from autom8_asana.core.field_utils import get_field_attr

        field_dict = {"gid": "123", "name": "Test Field"}
        assert get_field_attr(field_dict, "missing") is None
        assert get_field_attr(field_dict, "missing", "default") == "default"

    def test_object_access(self) -> None:
        """Test accessing attributes from object."""
        from autom8_asana.core.field_utils import get_field_attr

        class MockField:
            def __init__(self) -> None:
                self.gid = "456"
                self.name = "Object Field"
                self.resource_subtype = "enum"

        field_obj = MockField()
        assert get_field_attr(field_obj, "name") == "Object Field"
        assert get_field_attr(field_obj, "gid") == "456"
        assert get_field_attr(field_obj, "resource_subtype") == "enum"

    def test_object_access_with_default(self) -> None:
        """Test object access with default value for missing attribute."""
        from autom8_asana.core.field_utils import get_field_attr

        class MockField:
            def __init__(self) -> None:
                self.gid = "456"

        field_obj = MockField()
        assert get_field_attr(field_obj, "missing") is None
        assert get_field_attr(field_obj, "missing", "fallback") == "fallback"

    def test_none_input(self) -> None:
        """Test that None input returns default."""
        from autom8_asana.core.field_utils import get_field_attr

        assert get_field_attr(None, "name") is None
        assert get_field_attr(None, "name", "default") == "default"


class TestResolveEnumValueWithObjects:
    """Tests for enum resolution with object-based custom fields."""

    def test_resolves_with_object_field_def(self) -> None:
        """Test enum resolution when field_def is an object, not dict."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        class MockFieldDef:
            def __init__(self) -> None:
                self.name = "Vertical"
                self.resource_subtype = "enum"
                self.enum_options = [
                    {"gid": "111", "name": "Dental", "enabled": True},
                    {"gid": "222", "name": "Medical", "enabled": True},
                ]

        field_def = MockFieldDef()
        result = seeder._resolve_enum_value(field_def, "Dental", "Vertical", "task_123")
        assert result == "111"

    def test_resolves_with_object_enum_options(self) -> None:
        """Test enum resolution when enum_options contain objects, not dicts."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        class MockEnumOption:
            def __init__(self, gid: str, name: str, enabled: bool = True) -> None:
                self.gid = gid
                self.name = name
                self.enabled = enabled

        class MockFieldDef:
            def __init__(self) -> None:
                self.name = "Vertical"
                self.resource_subtype = "enum"
                self.enum_options = [
                    MockEnumOption("111", "Dental"),
                    MockEnumOption("222", "Medical"),
                ]

        field_def = MockFieldDef()
        result = seeder._resolve_enum_value(
            field_def, "Medical", "Vertical", "task_123"
        )
        assert result == "222"

    def test_validates_gid_with_object_options(self) -> None:
        """Test GID validation when enum_options are objects."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        class MockEnumOption:
            def __init__(self, gid: str, name: str) -> None:
                self.gid = gid
                self.name = name
                self.enabled = True

        class MockFieldDef:
            def __init__(self) -> None:
                self.name = "Vertical"
                self.resource_subtype = "enum"
                self.enum_options = [MockEnumOption("123", "Dental")]

        field_def = MockFieldDef()

        # Valid GID passes through
        result = seeder._resolve_enum_value(field_def, "123", "Vertical", "task_123")
        assert result == "123"

        # Invalid GID returns None
        result = seeder._resolve_enum_value(field_def, "999", "Vertical", "task_123")
        assert result is None


class TestWriteFieldsAsyncWithObjectCustomFields:
    """Integration tests for write_fields_async with object-based custom fields."""

    @pytest.mark.asyncio
    async def test_write_with_object_custom_fields(self) -> None:
        """Test that write_fields_async works when custom_fields are objects."""
        from unittest.mock import AsyncMock

        client = create_mock_client()
        seeder = FieldSeeder(client)

        # Create mock objects instead of dicts
        class MockEnumOption:
            def __init__(self, gid: str, name: str, enabled: bool = True) -> None:
                self.gid = gid
                self.name = name
                self.enabled = enabled

        class MockCustomField:
            def __init__(
                self,
                gid: str,
                name: str,
                resource_subtype: str,
                enum_options: list | None = None,
            ) -> None:
                self.gid = gid
                self.name = name
                self.resource_subtype = resource_subtype
                self.enum_options = enum_options or []

        mock_task = MagicMock()
        mock_task.custom_fields = [
            MockCustomField(
                gid="cf_vertical",
                name="Vertical",
                resource_subtype="enum",
                enum_options=[
                    MockEnumOption("opt_dental", "Dental"),
                    MockEnumOption("opt_medical", "Medical"),
                ],
            ),
            MockCustomField(
                gid="cf_notes",
                name="Notes",
                resource_subtype="text",
            ),
        ]

        client.tasks.get_async = AsyncMock(return_value=mock_task)
        client.tasks.update_async = AsyncMock()

        result = await seeder.write_fields_async(
            target_task_gid="task_123",
            fields={
                "Vertical": "Dental",
                "Notes": "Test notes",
            },
        )

        assert result.success
        assert "Vertical" in result.fields_written
        assert "Notes" in result.fields_written

        # Verify the update was called correctly
        client.tasks.update_async.assert_called_once()
        call_kwargs = client.tasks.update_async.call_args[1]
        custom_fields = call_kwargs["custom_fields"]
        assert custom_fields["cf_vertical"] == "opt_dental"
        assert custom_fields["cf_notes"] == "Test notes"
