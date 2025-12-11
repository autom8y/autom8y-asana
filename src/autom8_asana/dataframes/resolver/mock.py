"""Mock implementation of CustomFieldResolver for testing.

Per FR-TEST-001: Provides mock resolver injection for testing without
live Asana connection.

Per FR-TEST-003: Supports resolution from fixture data without Asana API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.dataframes.resolver.normalizer import NameNormalizer

if TYPE_CHECKING:
    from autom8_asana.models.custom_field import CustomField
    from autom8_asana.models.task import Task


class MockCustomFieldResolver:
    """Mock resolver for testing without live Asana connection.

    Configure with name->value mappings instead of building from tasks.
    Values are returned directly (no extraction from task.custom_fields).

    Per FR-TEST-001: Test can inject MockResolver with pre-defined mappings.
    Per FR-TEST-003: Works offline with fixture data.

    Example:
        >>> from decimal import Decimal
        >>> resolver = MockCustomFieldResolver({
        ...     "mrr": Decimal("5000"),
        ...     "weekly_ad_spend": Decimal("1000"),
        ...     "products": ["Product A", "Product B"],
        ... })
        >>> resolver.get_value(None, "cf:MRR")
        Decimal('5000')
        >>> resolver.get_value(None, "cf:Products")
        ['Product A', 'Product B']
        >>> resolver.has_field("cf:MRR")
        True
        >>> resolver.has_field("cf:nonexistent")
        False

    Attributes:
        strict: If True, raise KeyError on missing fields. Default False.
    """

    def __init__(
        self,
        field_values: dict[str, Any],
        *,
        strict: bool = False,
    ) -> None:
        """Initialize mock resolver with pre-defined field values.

        Args:
            field_values: Mapping of field name -> value.
                          Field names are normalized for lookup.
            strict: If True, raise KeyError on missing fields.
        """
        self._strict = strict
        self._values = field_values
        # Pre-normalize keys for O(1) lookup
        self._normalized: dict[str, Any] = {
            NameNormalizer.normalize(k): v for k, v in field_values.items()
        }
        # Track original names for debugging
        self._name_map: dict[str, str] = {
            NameNormalizer.normalize(k): k for k in field_values.keys()
        }

    def build_index(self, custom_fields: list[CustomField]) -> None:
        """No-op for mock - values pre-configured.

        Args:
            custom_fields: Ignored in mock implementation
        """
        # No-op: mock resolver has pre-configured values
        pass

    def resolve(self, field_name: str) -> str | None:
        """Return synthetic GID if field exists in mock data.

        Args:
            field_name: Field name with optional prefix

        Returns:
            Synthetic GID (mock_gid_{normalized_name}) if field exists,
            None otherwise
        """
        # Handle gid: prefix - return directly
        if field_name.startswith("gid:"):
            return field_name[4:]

        # Strip cf: prefix if present
        lookup = field_name[3:] if field_name.startswith("cf:") else field_name
        normalized = NameNormalizer.normalize(lookup)

        if normalized in self._normalized:
            return f"mock_gid_{normalized}"
        return None

    def get_value(
        self,
        task: Task | None,
        field_name: str,
        expected_type: type | None = None,
    ) -> Any:
        """Return pre-configured value for field.

        The task parameter is ignored - values come from the mock
        configuration, not the task.

        Args:
            task: Ignored in mock implementation
            field_name: Field name with optional prefix
            expected_type: Ignored in mock (values pre-typed)

        Returns:
            Pre-configured value if field exists, None otherwise

        Raises:
            KeyError: If strict mode and field not found
        """
        # Handle gid: prefix - not supported in mock
        if field_name.startswith("gid:"):
            if self._strict:
                raise KeyError(f"GID lookup not supported in mock: {field_name}")
            return None

        lookup = field_name[3:] if field_name.startswith("cf:") else field_name
        normalized = NameNormalizer.normalize(lookup)

        if normalized in self._normalized:
            return self._normalized[normalized]

        if self._strict:
            raise KeyError(f"Mock field not configured: {field_name}")
        return None

    def has_field(self, field_name: str) -> bool:
        """Check if field exists in mock configuration.

        Args:
            field_name: Field name with optional prefix

        Returns:
            True if field is in mock configuration
        """
        if field_name.startswith("gid:"):
            return False

        lookup = field_name[3:] if field_name.startswith("cf:") else field_name
        normalized = NameNormalizer.normalize(lookup)
        return normalized in self._normalized

    def get_configured_fields(self) -> list[str]:
        """Get list of configured field names (original, not normalized).

        Returns:
            List of original field names passed to constructor
        """
        return list(self._values.keys())

    def add_field(self, name: str, value: Any) -> None:
        """Add a field to the mock configuration.

        Useful for incrementally building mock data in tests.

        Args:
            name: Field name
            value: Field value
        """
        self._values[name] = value
        normalized = NameNormalizer.normalize(name)
        self._normalized[normalized] = value
        self._name_map[normalized] = name


class FailingResolver:
    """A resolver that fails on specific fields for error path testing.

    Per FR-TEST-004: Provides FailingResolver for error path testing.

    Example:
        >>> resolver = FailingResolver(fail_on=["mrr", "discount"])
        >>> resolver.get_value(task, "cf:MRR")  # Raises
        Traceback (most recent call last):
        ...
        KeyError: Configured to fail on field: cf:MRR
    """

    def __init__(
        self,
        fail_on: list[str],
        *,
        fallback: MockCustomFieldResolver | None = None,
    ) -> None:
        """Initialize failing resolver.

        Args:
            fail_on: List of field names (normalized) that should raise errors
            fallback: Optional fallback resolver for non-failing fields
        """
        self._fail_on = {NameNormalizer.normalize(f) for f in fail_on}
        self._fallback = fallback

    def build_index(self, custom_fields: list[CustomField]) -> None:
        """No-op for test resolver."""
        if self._fallback:
            self._fallback.build_index(custom_fields)

    def resolve(self, field_name: str) -> str | None:
        """Check if should fail, otherwise delegate to fallback.

        Raises:
            KeyError: If field is in fail_on list
        """
        lookup = field_name[3:] if field_name.startswith("cf:") else field_name
        normalized = NameNormalizer.normalize(lookup)

        if normalized in self._fail_on:
            raise KeyError(f"Configured to fail on field: {field_name}")

        if self._fallback:
            return self._fallback.resolve(field_name)
        return None

    def get_value(
        self,
        task: Task | None,
        field_name: str,
        expected_type: type | None = None,
    ) -> Any:
        """Check if should fail, otherwise delegate to fallback.

        Raises:
            KeyError: If field is in fail_on list
        """
        lookup = field_name[3:] if field_name.startswith("cf:") else field_name
        normalized = NameNormalizer.normalize(lookup)

        if normalized in self._fail_on:
            raise KeyError(f"Configured to fail on field: {field_name}")

        if self._fallback:
            return self._fallback.get_value(task, field_name, expected_type)
        return None

    def has_field(self, field_name: str) -> bool:
        """Check if field would fail or exists in fallback."""
        lookup = field_name[3:] if field_name.startswith("cf:") else field_name
        normalized = NameNormalizer.normalize(lookup)

        if normalized in self._fail_on:
            return False

        if self._fallback:
            return self._fallback.has_field(field_name)
        return False
