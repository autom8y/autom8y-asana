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

from autom8_asana.dataframes.resolver import (
    CustomFieldResolver,
    DefaultCustomFieldResolver,
    FailingResolver,
    MockCustomFieldResolver,
    NameNormalizer,
)


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


class MockTask:
    """Mock Task object for testing."""

    def __init__(self, custom_fields: list[dict[str, Any]] | None = None) -> None:
        self.custom_fields = custom_fields or []


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
        """Test number value coerced to Decimal."""
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
        value = resolver.get_value(task, "cf:MRR", Decimal)  # type: ignore[arg-type]
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
