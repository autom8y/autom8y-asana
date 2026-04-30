"""Unit tests for custom field resolver package.

Per TDD-0009.1: Tests for NameNormalizer, DefaultCustomFieldResolver,
and MockCustomFieldResolver components.
"""

from __future__ import annotations

import threading
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from autom8_asana.dataframes.models.schema import ColumnDef
from autom8_asana.dataframes.resolver import (
    CustomFieldResolver,
    DefaultCustomFieldResolver,
    FailingResolver,
    MockCustomFieldResolver,
    NameNormalizer,
)
from tests._shared.mocks import MockTask

# ============================================================================
# Test Fixtures
# ============================================================================


class MockCustomField:
    """Mock CustomField object for testing."""

    def __init__(
        self,
        gid: str,
        name: str,
        resource_subtype: str = "text",
        text_value: str | None = None,
        number_value: float | None = None,
        enum_value: dict[str, Any] | None = None,
        multi_enum_values: list[dict[str, Any]] | None = None,
        display_value: str | None = None,
        date_value: dict[str, Any] | None = None,
        people_value: list[dict[str, Any]] | None = None,
    ) -> None:
        self.gid = gid
        self.name = name
        self.resource_subtype = resource_subtype
        self.text_value = text_value
        self.number_value = number_value
        self.enum_value = enum_value
        self.multi_enum_values = multi_enum_values
        self.display_value = display_value
        self.date_value = date_value
        self.people_value = people_value


# ============================================================================
# TestNameNormalizer
# ============================================================================


class TestNameNormalizer:
    """Tests for NameNormalizer class."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        NameNormalizer.clear_cache()

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            # Basic cases
            ("Weekly Ad Spend", "weeklyadspend"),
            ("weekly_ad_spend", "weeklyadspend"),
            ("WeeklyAdSpend", "weeklyadspend"),
            # Acronyms
            ("MRR", "mrr"),
            ("ID", "id"),
            ("ARR", "arr"),
            # Hyphenated
            ("Monthly-Recurring-Revenue", "monthlyrecurringrevenue"),
            ("monthly-recurring-revenue", "monthlyrecurringrevenue"),
            # Mixed case
            ("Contact Email", "contactemail"),
            ("contact_email", "contactemail"),
            ("ContactEmail", "contactemail"),
            # Spaces
            ("  Spaced  Out  ", "spacedout"),
            ("Spaced Out", "spacedout"),
            # Numbers
            ("Product123", "product123"),
            ("123abc", "123abc"),
            # Special characters
            ("Field (New)", "fieldnew"),
            ("Field: Value", "fieldvalue"),
            ("Field/Value", "fieldvalue"),
            # Empty/edge cases
            ("", ""),
            ("   ", ""),
            # Single character
            ("X", "x"),
            ("1", "1"),
        ],
    )
    def test_normalize(self, input_name: str, expected: str) -> None:
        """Test normalization of various field name formats."""
        assert NameNormalizer.normalize(input_name) == expected

    def test_is_match_positive(self) -> None:
        """Test is_match returns True for equivalent names."""
        assert NameNormalizer.is_match("Weekly Ad Spend", "weekly_ad_spend")
        assert NameNormalizer.is_match("MRR", "mrr")
        assert NameNormalizer.is_match("Contact Email", "ContactEmail")
        assert NameNormalizer.is_match("ID", "id")
        assert NameNormalizer.is_match("Employee ID", "employee_id")

    def test_is_match_negative(self) -> None:
        """Test is_match returns False for different names."""
        assert not NameNormalizer.is_match("MRR", "ARR")
        assert not NameNormalizer.is_match("Weekly Ad Spend", "Monthly Ad Spend")
        assert not NameNormalizer.is_match("Contact Email", "Contact Phone")

    def test_normalize_caching(self) -> None:
        """Test that LRU cache is working."""
        # First call - cache miss
        NameNormalizer.normalize("test_value")
        info1 = NameNormalizer.cache_info()
        assert info1["misses"] >= 1

        # Second call - cache hit
        NameNormalizer.normalize("test_value")
        info2 = NameNormalizer.cache_info()
        assert info2["hits"] >= 1

    def test_clear_cache(self) -> None:
        """Test cache clearing."""
        NameNormalizer.normalize("test_value")
        info1 = NameNormalizer.cache_info()
        assert info1["currsize"] >= 1

        NameNormalizer.clear_cache()
        info2 = NameNormalizer.cache_info()
        assert info2["currsize"] == 0


# ============================================================================
# TestDefaultCustomFieldResolver
# ============================================================================


class TestDefaultCustomFieldResolver:
    """Tests for DefaultCustomFieldResolver class."""

    def test_build_index(self) -> None:
        """Test building index from custom fields."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="MRR", resource_subtype="number"),
            MockCustomField(gid="456", name="Weekly Ad Spend", resource_subtype="number"),
            MockCustomField(gid="789", name="Products", resource_subtype="multi_enum"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        assert resolver.resolve("cf:MRR") == "123"
        assert resolver.resolve("cf:Weekly Ad Spend") == "456"
        assert resolver.resolve("cf:Products") == "789"

    def test_resolve_normalized(self) -> None:
        """Test resolution with normalized names."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="MRR", resource_subtype="number"),
            MockCustomField(gid="456", name="Weekly Ad Spend", resource_subtype="number"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        # Various normalizations should resolve to same GID
        assert resolver.resolve("cf:mrr") == "123"
        assert resolver.resolve("cf:MRR") == "123"
        assert resolver.resolve("cf:weekly_ad_spend") == "456"
        assert resolver.resolve("cf:WeeklyAdSpend") == "456"

    def test_resolve_without_prefix(self) -> None:
        """Test resolution without cf: prefix."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="MRR", resource_subtype="number"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        # Should work without cf: prefix
        assert resolver.resolve("MRR") == "123"
        assert resolver.resolve("mrr") == "123"

    def test_resolve_explicit_gid(self) -> None:
        """Test explicit GID resolution bypasses index."""
        resolver = DefaultCustomFieldResolver()

        # No index built, but gid: prefix should work
        assert resolver.resolve("gid:999") == "999"
        assert resolver.resolve("gid:123456") == "123456"

    def test_resolve_missing_field_lenient(self) -> None:
        """Test missing field returns None in lenient mode."""
        resolver = DefaultCustomFieldResolver(strict=False)
        resolver.build_index([])

        assert resolver.resolve("cf:nonexistent") is None

    def test_resolve_missing_field_strict(self) -> None:
        """Test missing field raises in strict mode."""
        resolver = DefaultCustomFieldResolver(strict=True)
        resolver.build_index([])

        mock_task = MockTask()
        with pytest.raises(KeyError, match="Cannot resolve custom field"):
            resolver.get_value(mock_task, "cf:nonexistent")  # type: ignore[arg-type]

    def test_has_field(self) -> None:
        """Test has_field method."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="MRR", resource_subtype="number"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        assert resolver.has_field("cf:MRR") is True
        assert resolver.has_field("cf:mrr") is True
        assert resolver.has_field("cf:nonexistent") is False
        assert resolver.has_field("gid:999") is True  # gid: always resolvable

    def test_get_value_text(self) -> None:
        """Test extracting text field value."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="Specialty", resource_subtype="text"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        task = MockTask(
            custom_fields=[
                {
                    "gid": "123",
                    "name": "Specialty",
                    "resource_subtype": "text",
                    "text_value": "Cardiology",
                }
            ]
        )
        value = resolver.get_value(task, "cf:Specialty")  # type: ignore[arg-type]
        assert value == "Cardiology"

    def test_get_value_number(self) -> None:
        """Test extracting number field value."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="MRR", resource_subtype="number"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        task = MockTask(
            custom_fields=[
                {
                    "gid": "123",
                    "name": "MRR",
                    "resource_subtype": "number",
                    "number_value": 5000.0,
                }
            ]
        )
        value = resolver.get_value(task, "cf:MRR")  # type: ignore[arg-type]
        assert value == 5000.0

    def test_get_value_number_with_decimal_coercion(self) -> None:
        """Test number value coerced to Decimal via column_def."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="MRR", resource_subtype="number"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        task = MockTask(
            custom_fields=[
                {
                    "gid": "123",
                    "name": "MRR",
                    "resource_subtype": "number",
                    "number_value": 5000.50,
                }
            ]
        )
        column_def = ColumnDef(
            name="mrr",
            dtype="Decimal",
            source="cf:MRR",
        )
        value = resolver.get_value(
            task,
            "cf:MRR",
            column_def=column_def,  # type: ignore[arg-type]
        )
        assert value == Decimal("5000.5")
        assert isinstance(value, Decimal)

    def test_get_value_enum(self) -> None:
        """Test extracting enum field value."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="Vertical", resource_subtype="enum"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        task = MockTask(
            custom_fields=[
                {
                    "gid": "123",
                    "name": "Vertical",
                    "resource_subtype": "enum",
                    "enum_value": {"gid": "456", "name": "Healthcare"},
                }
            ]
        )
        value = resolver.get_value(task, "cf:Vertical")  # type: ignore[arg-type]
        assert value == "Healthcare"

    def test_get_value_multi_enum(self) -> None:
        """Test extracting multi-enum field value."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="Products", resource_subtype="multi_enum"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        task = MockTask(
            custom_fields=[
                {
                    "gid": "123",
                    "name": "Products",
                    "resource_subtype": "multi_enum",
                    "multi_enum_values": [
                        {"gid": "a", "name": "Product A"},
                        {"gid": "b", "name": "Product B"},
                    ],
                }
            ]
        )
        value = resolver.get_value(task, "cf:Products")  # type: ignore[arg-type]
        assert value == ["Product A", "Product B"]

    def test_get_value_missing_field_on_task(self) -> None:
        """Test field not present on task returns None."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="MRR", resource_subtype="number"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        # Task doesn't have the field
        task = MockTask(custom_fields=[])
        value = resolver.get_value(task, "cf:MRR")  # type: ignore[arg-type]
        assert value is None

    def test_build_index_idempotent(self) -> None:
        """Test that build_index only runs once."""
        resolver = DefaultCustomFieldResolver()
        fields1 = [MockCustomField(gid="111", name="Field1", resource_subtype="text")]
        fields2 = [MockCustomField(gid="222", name="Field2", resource_subtype="text")]

        resolver.build_index(fields1)  # type: ignore[arg-type]
        resolver.build_index(fields2)  # type: ignore[arg-type]  # Should be ignored

        # Should still have first index
        assert resolver.resolve("cf:Field1") == "111"
        assert resolver.resolve("cf:Field2") is None

    def test_thread_safety(self) -> None:
        """Test concurrent index building is thread-safe."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="MRR", resource_subtype="number"),
        ]
        results: list[str | None] = []

        def build_and_resolve() -> None:
            resolver.build_index(custom_fields)  # type: ignore[arg-type]
            result = resolver.resolve("cf:MRR")
            results.append(result)

        threads = [threading.Thread(target=build_and_resolve) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        # All threads should get the same result
        assert all(r == "123" for r in results)
        assert len(results) == 10

    def test_get_resolution_stats(self) -> None:
        """Test resolution statistics."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="MRR", resource_subtype="number"),
            MockCustomField(gid="456", name="ARR", resource_subtype="number"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        stats = resolver.get_resolution_stats()
        assert stats["indexed_fields"] == 2
        assert len(stats["field_names"]) == 2

    def test_get_unresolved_fields(self) -> None:
        """Test tracking unresolved field lookups."""
        resolver = DefaultCustomFieldResolver()
        resolver.build_index([])

        # Try to resolve non-existent fields
        resolver.resolve("cf:missing1")
        resolver.resolve("cf:missing2")

        unresolved = resolver.get_unresolved_fields()
        assert "cf:missing1" in unresolved
        assert "cf:missing2" in unresolved

    def test_clear_cache(self) -> None:
        """Test cache clearing allows rebuild."""
        resolver = DefaultCustomFieldResolver()
        fields1 = [MockCustomField(gid="111", name="Field1", resource_subtype="text")]
        fields2 = [MockCustomField(gid="222", name="Field2", resource_subtype="text")]

        resolver.build_index(fields1)  # type: ignore[arg-type]
        assert resolver.resolve("cf:Field1") == "111"

        resolver.clear_cache()
        resolver.build_index(fields2)  # type: ignore[arg-type]

        # Now should have second index
        assert resolver.resolve("cf:Field1") is None
        assert resolver.resolve("cf:Field2") == "222"

    def test_duplicate_normalized_names(self) -> None:
        """Test handling of duplicate names after normalization."""
        resolver = DefaultCustomFieldResolver()
        # Both normalize to "mrr"
        custom_fields = [
            MockCustomField(gid="111", name="MRR", resource_subtype="number"),
            MockCustomField(gid="222", name="mrr", resource_subtype="number"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        # First match wins
        assert resolver.resolve("cf:MRR") == "111"
        assert resolver.resolve("cf:mrr") == "111"


# ============================================================================
# TestMockCustomFieldResolver
# ============================================================================


class TestMockCustomFieldResolver:
    """Tests for MockCustomFieldResolver class."""

    def test_basic_mock_values(self) -> None:
        """Test basic mock value retrieval."""
        resolver = MockCustomFieldResolver(
            {
                "mrr": Decimal("5000"),
                "products": ["A", "B"],
                "vertical": "Healthcare",
            }
        )

        assert resolver.get_value(None, "cf:MRR") == Decimal("5000")
        assert resolver.get_value(None, "cf:Products") == ["A", "B"]
        assert resolver.get_value(None, "cf:Vertical") == "Healthcare"

    def test_normalized_lookup(self) -> None:
        """Test mock values accessed via normalized names."""
        resolver = MockCustomFieldResolver({"weekly_ad_spend": Decimal("1000")})

        # Various normalizations should work
        assert resolver.get_value(None, "cf:weekly_ad_spend") == Decimal("1000")
        assert resolver.get_value(None, "cf:Weekly Ad Spend") == Decimal("1000")
        assert resolver.get_value(None, "cf:WeeklyAdSpend") == Decimal("1000")

    def test_missing_field_lenient(self) -> None:
        """Test missing mock field returns None."""
        resolver = MockCustomFieldResolver({"mrr": Decimal("5000")})

        assert resolver.get_value(None, "cf:nonexistent") is None

    def test_missing_field_strict(self) -> None:
        """Test strict mode raises on missing field."""
        resolver = MockCustomFieldResolver({"mrr": Decimal("5000")}, strict=True)

        with pytest.raises(KeyError, match="Mock field not configured"):
            resolver.get_value(None, "cf:nonexistent")

    def test_has_field(self) -> None:
        """Test has_field method."""
        resolver = MockCustomFieldResolver(
            {
                "mrr": Decimal("5000"),
                "products": ["A"],
            }
        )

        assert resolver.has_field("cf:MRR") is True
        assert resolver.has_field("cf:Products") is True
        assert resolver.has_field("cf:nonexistent") is False

    def test_resolve_returns_synthetic_gid(self) -> None:
        """Test resolve returns synthetic GID."""
        resolver = MockCustomFieldResolver({"mrr": Decimal("5000")})

        gid = resolver.resolve("cf:MRR")
        assert gid == "mock_gid_mrr"

    def test_build_index_noop(self) -> None:
        """Test build_index is a no-op."""
        resolver = MockCustomFieldResolver({"mrr": Decimal("5000")})

        # Should not affect mock values
        resolver.build_index([MagicMock()])
        assert resolver.get_value(None, "cf:MRR") == Decimal("5000")

    def test_get_configured_fields(self) -> None:
        """Test listing configured fields."""
        resolver = MockCustomFieldResolver(
            {
                "mrr": Decimal("5000"),
                "Weekly Ad Spend": Decimal("1000"),
            }
        )

        fields = resolver.get_configured_fields()
        assert "mrr" in fields
        assert "Weekly Ad Spend" in fields

    def test_add_field(self) -> None:
        """Test dynamically adding fields."""
        resolver = MockCustomFieldResolver({})

        resolver.add_field("mrr", Decimal("5000"))
        assert resolver.get_value(None, "cf:MRR") == Decimal("5000")

    def test_gid_prefix_not_supported(self) -> None:
        """Test gid: prefix not supported in mock."""
        resolver = MockCustomFieldResolver({}, strict=True)

        with pytest.raises(KeyError, match="GID lookup not supported"):
            resolver.get_value(None, "gid:123")


# ============================================================================
# TestFailingResolver
# ============================================================================


class TestFailingResolver:
    """Tests for FailingResolver class."""

    def test_fails_on_specified_fields(self) -> None:
        """Test resolver fails on specified fields."""
        resolver = FailingResolver(fail_on=["mrr", "discount"])

        with pytest.raises(KeyError, match="Configured to fail"):
            resolver.resolve("cf:MRR")

        with pytest.raises(KeyError, match="Configured to fail"):
            resolver.get_value(None, "cf:Discount")

    def test_fallback_to_mock(self) -> None:
        """Test fallback to mock resolver for non-failing fields."""
        mock = MockCustomFieldResolver({"products": ["A", "B"]})
        resolver = FailingResolver(fail_on=["mrr"], fallback=mock)

        # Should fail
        with pytest.raises(KeyError):
            resolver.get_value(None, "cf:MRR")

        # Should work via fallback
        assert resolver.get_value(None, "cf:Products") == ["A", "B"]

    def test_has_field_excludes_failing(self) -> None:
        """Test has_field returns False for failing fields."""
        mock = MockCustomFieldResolver({"mrr": Decimal("5000"), "products": ["A"]})
        resolver = FailingResolver(fail_on=["mrr"], fallback=mock)

        assert resolver.has_field("cf:MRR") is False
        assert resolver.has_field("cf:Products") is True


# ============================================================================
# TestProtocolCompliance
# ============================================================================


class TestProtocolCompliance:
    """Test that implementations satisfy the CustomFieldResolver protocol."""

    def test_default_resolver_is_protocol(self) -> None:
        """Test DefaultCustomFieldResolver satisfies Protocol."""
        resolver = DefaultCustomFieldResolver()
        assert isinstance(resolver, CustomFieldResolver)

    def test_mock_resolver_is_protocol(self) -> None:
        """Test MockCustomFieldResolver satisfies Protocol."""
        resolver = MockCustomFieldResolver({})
        assert isinstance(resolver, CustomFieldResolver)

    def test_failing_resolver_is_protocol(self) -> None:
        """Test FailingResolver satisfies Protocol."""
        resolver = FailingResolver(fail_on=[])
        assert isinstance(resolver, CustomFieldResolver)


# ============================================================================
# TestSchemaAwareCoercion
# ============================================================================


class TestSchemaAwareCoercion:
    """Tests for _coerce_with_schema() method in DefaultCustomFieldResolver.

    Per TDD-custom-field-type-coercion FR-002/FR-003: Tests schema-aware coercion
    using column_def parameter.
    """

    def test_coerce_with_schema_multi_enum_to_string(self) -> None:
        """Test multi_enum list coerced to comma-separated string via column_def."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="Products", resource_subtype="multi_enum"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        task = MockTask(
            custom_fields=[
                {
                    "gid": "123",
                    "name": "Products",
                    "resource_subtype": "multi_enum",
                    "multi_enum_values": [
                        {"gid": "a", "name": "Product A"},
                        {"gid": "b", "name": "Product B"},
                    ],
                }
            ]
        )

        # Define column with Utf8 dtype (should join list to string)
        column_def = ColumnDef(
            name="products",
            dtype="Utf8",
            source="cf:Products",
        )

        value = resolver.get_value(
            task,
            "cf:Products",
            column_def=column_def,  # type: ignore[arg-type]
        )
        assert value == "Product A, Product B"

    def test_coerce_with_schema_list_dtype_passthrough(self) -> None:
        """Test list value passed through when column dtype is List[Utf8]."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="Products", resource_subtype="multi_enum"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        task = MockTask(
            custom_fields=[
                {
                    "gid": "123",
                    "name": "Products",
                    "resource_subtype": "multi_enum",
                    "multi_enum_values": [
                        {"gid": "a", "name": "Product A"},
                        {"gid": "b", "name": "Product B"},
                    ],
                }
            ]
        )

        # Define column with List[Utf8] dtype (should preserve list)
        column_def = ColumnDef(
            name="products",
            dtype="List[Utf8]",
            source="cf:Products",
        )

        value = resolver.get_value(
            task,
            "cf:Products",
            column_def=column_def,  # type: ignore[arg-type]
        )
        assert value == ["Product A", "Product B"]

    def test_coerce_with_schema_number_to_decimal(self) -> None:
        """Test number value coerced to Decimal via column_def."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="MRR", resource_subtype="number"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        task = MockTask(
            custom_fields=[
                {
                    "gid": "123",
                    "name": "MRR",
                    "resource_subtype": "number",
                    "number_value": 5000.50,
                }
            ]
        )

        column_def = ColumnDef(
            name="mrr",
            dtype="Decimal",
            source="cf:MRR",
        )

        value = resolver.get_value(
            task,
            "cf:MRR",
            column_def=column_def,  # type: ignore[arg-type]
        )
        assert value == Decimal("5000.5")
        assert isinstance(value, Decimal)

    def test_coerce_with_schema_number_to_float(self) -> None:
        """Test number value coerced to Float64 via column_def."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="Score", resource_subtype="number"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        task = MockTask(
            custom_fields=[
                {
                    "gid": "123",
                    "name": "Score",
                    "resource_subtype": "number",
                    "number_value": 95.5,
                }
            ]
        )

        column_def = ColumnDef(
            name="score",
            dtype="Float64",
            source="cf:Score",
        )

        value = resolver.get_value(
            task,
            "cf:Score",
            column_def=column_def,  # type: ignore[arg-type]
        )
        assert value == 95.5
        assert isinstance(value, float)

    def test_coerce_with_schema_empty_list_to_none(self) -> None:
        """Test empty multi_enum list coerced to None for Utf8 dtype."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="Tags", resource_subtype="multi_enum"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        task = MockTask(
            custom_fields=[
                {
                    "gid": "123",
                    "name": "Tags",
                    "resource_subtype": "multi_enum",
                    "multi_enum_values": [],
                }
            ]
        )

        column_def = ColumnDef(
            name="tags",
            dtype="Utf8",
            source="cf:Tags",
        )

        value = resolver.get_value(
            task,
            "cf:Tags",
            column_def=column_def,  # type: ignore[arg-type]
        )
        assert value is None

    def test_column_def_coercion_multi_enum_to_string(self) -> None:
        """Test column_def coercion converts multi_enum to string."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="Products", resource_subtype="multi_enum"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        task = MockTask(
            custom_fields=[
                {
                    "gid": "123",
                    "name": "Products",
                    "resource_subtype": "multi_enum",
                    "multi_enum_values": [
                        {"gid": "a", "name": "Product A"},
                    ],
                }
            ]
        )

        column_def = ColumnDef(
            name="products",
            dtype="Utf8",
            source="cf:Products",
        )

        value = resolver.get_value(
            task,  # type: ignore[arg-type]
            "cf:Products",
            column_def=column_def,
        )
        assert value == "Product A"
        assert isinstance(value, str)

    def test_coerce_with_schema_null_value(self) -> None:
        """Test null value is preserved through schema coercion."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="MRR", resource_subtype="number"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        task = MockTask(
            custom_fields=[
                {
                    "gid": "123",
                    "name": "MRR",
                    "resource_subtype": "number",
                    "number_value": None,
                }
            ]
        )

        column_def = ColumnDef(
            name="mrr",
            dtype="Decimal",
            source="cf:MRR",
        )

        value = resolver.get_value(
            task,
            "cf:MRR",
            column_def=column_def,  # type: ignore[arg-type]
        )
        assert value is None

    def test_coerce_with_schema_string_to_list(self) -> None:
        """Test single string wrapped in list for List[Utf8] dtype."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="Tag", resource_subtype="enum"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        task = MockTask(
            custom_fields=[
                {
                    "gid": "123",
                    "name": "Tag",
                    "resource_subtype": "enum",
                    "enum_value": {"gid": "a", "name": "SingleTag"},
                }
            ]
        )

        column_def = ColumnDef(
            name="tags",
            dtype="List[Utf8]",
            source="cf:Tag",
        )

        value = resolver.get_value(
            task,
            "cf:Tag",
            column_def=column_def,  # type: ignore[arg-type]
        )
        assert value == ["SingleTag"]
        assert isinstance(value, list)


# ============================================================================
# ADVERSARIAL TESTS - MockCustomFieldResolver Consistency
# Per TDD-custom-field-type-coercion validation
# ============================================================================


class TestAdversarialMockResolverConsistency:
    """Adversarial tests to verify MockCustomFieldResolver matches DefaultCustomFieldResolver.

    The mock resolver should behave identically to the real resolver when
    schema-aware coercion is applied via column_def parameter.
    """

    def test_mock_coerces_list_to_string_with_column_def(self) -> None:
        """Test MockCustomFieldResolver coerces list to string via column_def."""
        resolver = MockCustomFieldResolver({"products": ["Product A", "Product B", "Product C"]})

        column_def = ColumnDef(
            name="products",
            dtype="Utf8",
            source="cf:Products",
        )

        value = resolver.get_value(None, "cf:Products", column_def=column_def)
        assert value == "Product A, Product B, Product C"
        assert isinstance(value, str)

    def test_mock_coerces_empty_list_to_none(self) -> None:
        """Test MockCustomFieldResolver coerces empty list to None."""
        resolver = MockCustomFieldResolver({"tags": []})

        column_def = ColumnDef(
            name="tags",
            dtype="Utf8",
            source="cf:Tags",
        )

        value = resolver.get_value(None, "cf:Tags", column_def=column_def)
        assert value is None

    def test_mock_preserves_list_for_list_dtype(self) -> None:
        """Test MockCustomFieldResolver preserves list for List[Utf8] dtype."""
        resolver = MockCustomFieldResolver({"products": ["A", "B"]})

        column_def = ColumnDef(
            name="products",
            dtype="List[Utf8]",
            source="cf:Products",
        )

        value = resolver.get_value(None, "cf:Products", column_def=column_def)
        assert value == ["A", "B"]
        assert isinstance(value, list)

    def test_mock_coerces_string_to_list(self) -> None:
        """Test MockCustomFieldResolver wraps string in list for List[Utf8]."""
        resolver = MockCustomFieldResolver({"tag": "SingleValue"})

        column_def = ColumnDef(
            name="tags",
            dtype="List[Utf8]",
            source="cf:Tag",
        )

        value = resolver.get_value(None, "cf:Tag", column_def=column_def)
        assert value == ["SingleValue"]
        assert isinstance(value, list)

    def test_mock_coerces_number_to_decimal(self) -> None:
        """Test MockCustomFieldResolver coerces float to Decimal."""
        from decimal import Decimal

        resolver = MockCustomFieldResolver({"mrr": 5000.50})

        column_def = ColumnDef(
            name="mrr",
            dtype="Decimal",
            source="cf:MRR",
        )

        value = resolver.get_value(None, "cf:MRR", column_def=column_def)
        assert isinstance(value, Decimal)
        assert value == Decimal("5000.5")

    def test_mock_coerces_string_to_int(self) -> None:
        """Test MockCustomFieldResolver coerces string to Int64."""
        resolver = MockCustomFieldResolver({"count": "123"})

        column_def = ColumnDef(
            name="count",
            dtype="Int64",
            source="cf:Count",
        )

        value = resolver.get_value(None, "cf:Count", column_def=column_def)
        assert value == 123
        assert isinstance(value, int)

    def test_mock_without_column_def_returns_raw(self) -> None:
        """Test MockCustomFieldResolver returns raw value without column_def."""
        resolver = MockCustomFieldResolver({"products": ["A", "B"]})

        # No column_def - should return raw list
        value = resolver.get_value(None, "cf:Products")
        assert value == ["A", "B"]
        assert isinstance(value, list)

    def test_mock_consistency_with_default_multi_enum(self) -> None:
        """Verify Mock and Default produce same result for multi_enum field."""
        # Setup DefaultCustomFieldResolver
        default_resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="Products", resource_subtype="multi_enum"),
        ]
        default_resolver.build_index(custom_fields)  # type: ignore[arg-type]

        task = MockTask(
            custom_fields=[
                {
                    "gid": "123",
                    "name": "Products",
                    "resource_subtype": "multi_enum",
                    "multi_enum_values": [
                        {"gid": "a", "name": "Product A"},
                        {"gid": "b", "name": "Product B"},
                    ],
                }
            ]
        )

        # Setup MockCustomFieldResolver with same data
        mock_resolver = MockCustomFieldResolver({"products": ["Product A", "Product B"]})

        column_def = ColumnDef(
            name="products",
            dtype="Utf8",
            source="cf:Products",
        )

        # Both should produce the same result
        default_value = default_resolver.get_value(
            task,
            "cf:Products",
            column_def=column_def,  # type: ignore[arg-type]
        )
        mock_value = mock_resolver.get_value(None, "cf:Products", column_def=column_def)

        assert default_value == mock_value == "Product A, Product B"

    def test_mock_consistency_empty_multi_enum(self) -> None:
        """Verify Mock and Default produce same result for empty multi_enum."""
        # Setup DefaultCustomFieldResolver
        default_resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="Tags", resource_subtype="multi_enum"),
        ]
        default_resolver.build_index(custom_fields)  # type: ignore[arg-type]

        task = MockTask(
            custom_fields=[
                {
                    "gid": "123",
                    "name": "Tags",
                    "resource_subtype": "multi_enum",
                    "multi_enum_values": [],
                }
            ]
        )

        # Setup MockCustomFieldResolver with same data
        mock_resolver = MockCustomFieldResolver({"tags": []})

        column_def = ColumnDef(
            name="tags",
            dtype="Utf8",
            source="cf:Tags",
        )

        # Both should produce None
        default_value = default_resolver.get_value(
            task,
            "cf:Tags",
            column_def=column_def,  # type: ignore[arg-type]
        )
        mock_value = mock_resolver.get_value(None, "cf:Tags", column_def=column_def)

        assert default_value is None
        assert mock_value is None

    def test_mock_handles_unicode_in_coercion(self) -> None:
        """Test MockCustomFieldResolver handles Unicode during coercion."""
        resolver = MockCustomFieldResolver({"products": ["Product ", "Produkt Müller", ""]})

        column_def = ColumnDef(
            name="products",
            dtype="Utf8",
            source="cf:Products",
        )

        value = resolver.get_value(None, "cf:Products", column_def=column_def)
        assert "" in value
        assert "Müller" in value
        assert "" in value

    def test_mock_handles_none_in_list_during_coercion(self) -> None:
        """Test MockCustomFieldResolver filters None during list-to-string coercion."""
        resolver = MockCustomFieldResolver({"products": ["A", None, "B", None, "C"]})

        column_def = ColumnDef(
            name="products",
            dtype="Utf8",
            source="cf:Products",
        )

        value = resolver.get_value(None, "cf:Products", column_def=column_def)
        assert value == "A, B, C"


class TestAdversarialCoercionBehavior:
    """Tests for coercion behavior with column_def and raw value fallback."""

    def test_column_def_coerces_number_to_int(self) -> None:
        """Test column_def coerces number to Int64."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="MRR", resource_subtype="number"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        task = MockTask(
            custom_fields=[
                {
                    "gid": "123",
                    "name": "MRR",
                    "resource_subtype": "number",
                    "number_value": 100.5,
                }
            ]
        )

        column_def = ColumnDef(
            name="mrr",
            dtype="Int64",  # Integer, not Decimal
            source="cf:MRR",
        )

        value = resolver.get_value(
            task,  # type: ignore[arg-type]
            "cf:MRR",
            column_def=column_def,
        )
        assert isinstance(value, int)
        assert value == 100  # Truncated to int

    def test_no_coercion_when_no_column_def(self) -> None:
        """Test no coercion when column_def not provided."""
        resolver = DefaultCustomFieldResolver()
        custom_fields = [
            MockCustomField(gid="123", name="MRR", resource_subtype="number"),
        ]
        resolver.build_index(custom_fields)  # type: ignore[arg-type]

        task = MockTask(
            custom_fields=[
                {
                    "gid": "123",
                    "name": "MRR",
                    "resource_subtype": "number",
                    "number_value": 100.5,
                }
            ]
        )

        # No column_def - raw value returned
        value = resolver.get_value(task, "cf:MRR")  # type: ignore[arg-type]
        assert value == 100.5
        assert isinstance(value, float)


class TestAdversarialIntegrationEndToEnd:
    """End-to-end integration tests for the full extraction flow."""

    def test_unit_extractor_coerces_multi_enum_to_string(self) -> None:
        """Test UnitExtractor properly coerces multi_enum to string via schema."""
        from autom8_asana.dataframes.extractors.unit import UnitExtractor
        from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA
        from autom8_asana.models.task import Task

        # Create resolver with list value (simulating multi_enum)
        resolver = MockCustomFieldResolver(
            {
                "specialty": ["Dental", "Orthodontics"],
                "products": ["Product A", "Product B"],
            }
        )

        task = Task(
            gid="123",
            name="Test Unit",
            created_at="2024-01-01T00:00:00Z",
            modified_at="2024-01-01T00:00:00Z",
        )

        extractor = UnitExtractor(UNIT_SCHEMA, resolver)
        row = extractor.extract(task)

        # specialty has dtype Utf8, so list should be coerced to string
        assert row.specialty == "Dental, Orthodontics"
        assert isinstance(row.specialty, str)

        # products has dtype List[Utf8], so should remain list
        assert row.products == ["Product A", "Product B"]
        assert isinstance(row.products, list)

    def test_unit_extractor_empty_multi_enum_to_none(self) -> None:
        """Test UnitExtractor properly handles empty multi_enum (returns None)."""
        from autom8_asana.dataframes.extractors.unit import UnitExtractor
        from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA
        from autom8_asana.models.task import Task

        resolver = MockCustomFieldResolver(
            {
                "specialty": [],  # Empty list
                "vertical": [],
            }
        )

        task = Task(
            gid="123",
            name="Test Unit",
            created_at="2024-01-01T00:00:00Z",
            modified_at="2024-01-01T00:00:00Z",
        )

        extractor = UnitExtractor(UNIT_SCHEMA, resolver)
        row = extractor.extract(task)

        # Empty list should coerce to None for Utf8 dtype
        assert row.specialty is None
        assert row.vertical is None

    def test_contact_extractor_coercion(self) -> None:
        """Test ContactExtractor schema-aware coercion."""
        from autom8_asana.dataframes.extractors.contact import ContactExtractor
        from autom8_asana.dataframes.schemas.contact import CONTACT_SCHEMA
        from autom8_asana.models.task import Task

        resolver = MockCustomFieldResolver(
            {
                "full_name": "John Doe",
                "contact_email": "john@example.com",
            }
        )

        task = Task(
            gid="456",
            name="Test Contact",
            created_at="2024-01-01T00:00:00Z",
            modified_at="2024-01-01T00:00:00Z",
        )

        extractor = ContactExtractor(CONTACT_SCHEMA, resolver)
        row = extractor.extract(task)

        assert row.full_name == "John Doe"
        assert row.contact_email == "john@example.com"

    def test_extractor_handles_mixed_field_types(self) -> None:
        """Test extractor handles mix of custom fields with different types."""
        from autom8_asana.dataframes.extractors.unit import UnitExtractor
        from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA
        from autom8_asana.models.task import Task

        resolver = MockCustomFieldResolver(
            {
                "mrr": Decimal("5000.00"),  # Decimal
                "weekly_ad_spend": 1500.50,  # float
                "discount": "10.5",  # string that should become Decimal
                "specialty": ["Dental"],  # list that should become string
                "products": "SingleProduct",  # string that should become list
            }
        )

        task = Task(
            gid="789",
            name="Mixed Types",
            created_at="2024-01-01T00:00:00Z",
            modified_at="2024-01-01T00:00:00Z",
        )

        extractor = UnitExtractor(UNIT_SCHEMA, resolver)
        row = extractor.extract(task)

        # Verify proper coercion happened
        assert row.mrr == Decimal("5000.00")
        assert row.weekly_ad_spend == Decimal("1500.5")
        assert row.discount == Decimal("10.5")
        assert row.specialty == "Dental"
        assert row.products == ["SingleProduct"]
