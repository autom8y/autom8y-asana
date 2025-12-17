"""Integration tests for custom field name resolution.

Per TDD-TRIAGE-FIXES Issue #1: Strict mode name resolution with fail-fast validation.
"""

from __future__ import annotations

import pytest

from autom8_asana.exceptions import NameNotFoundError
from autom8_asana.models.custom_field_accessor import CustomFieldAccessor


class TestStrictModeNameResolution:
    """Test strict mode name resolution (default)."""

    def test_strict_mode_known_name_resolves(self) -> None:
        """Strict mode: known name resolves correctly."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "123", "name": "Priority"}],
            strict=True,
        )
        gid = accessor._resolve_gid("Priority")
        assert gid == "123"

    def test_strict_mode_case_insensitive(self) -> None:
        """Strict mode: name resolution is case-insensitive."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "123", "name": "Priority"}],
            strict=True,
        )
        gid = accessor._resolve_gid("priority")  # lowercase
        assert gid == "123"

    def test_strict_mode_numeric_gid_passthrough(self) -> None:
        """Strict mode: numeric strings passed through as GIDs."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "123", "name": "Priority"}],
            strict=True,
        )
        gid = accessor._resolve_gid("456")  # Numeric string
        assert gid == "456"  # Returned as-is

    def test_strict_mode_unknown_name_raises(self) -> None:
        """Strict mode: unknown name raises NameNotFoundError."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "123", "name": "Priority"}],
            strict=True,
        )
        with pytest.raises(NameNotFoundError) as exc:
            accessor._resolve_gid("UnknownField")
        assert "UnknownField" in str(exc.value)

    def test_strict_mode_error_includes_suggestions(self) -> None:
        """Strict mode: error includes fuzzy match suggestions."""
        accessor = CustomFieldAccessor(
            data=[
                {"gid": "1", "name": "Priority"},
                {"gid": "2", "name": "Status"},
                {"gid": "3", "name": "Budget"},
            ],
            strict=True,
        )
        with pytest.raises(NameNotFoundError) as exc:
            accessor._resolve_gid("Pririty")  # Typo: should be "Priority"
        assert "Priority" in str(exc.value)  # Suggested in error

    def test_strict_mode_error_shows_available_names(self) -> None:
        """Strict mode: error shows available field names (if ≤20)."""
        accessor = CustomFieldAccessor(
            data=[
                {"gid": "1", "name": "Priority"},
                {"gid": "2", "name": "Status"},
            ],
            strict=True,
        )
        with pytest.raises(NameNotFoundError) as exc:
            accessor._resolve_gid("Unknown")
        error_msg = str(exc.value)
        # Should show available names
        assert "Priority" in error_msg or "Status" in error_msg

    def test_strict_mode_is_default(self) -> None:
        """Strict mode is the default."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "123", "name": "Priority"}],
        )
        # Should raise on unknown name (strict is default)
        with pytest.raises(NameNotFoundError):
            accessor._resolve_gid("UnknownField")

    def test_strict_mode_whitespace_stripped(self) -> None:
        """Strict mode: whitespace is stripped during lookup."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "123", "name": "Priority"}],
            strict=True,
        )
        gid = accessor._resolve_gid("  Priority  ")
        assert gid == "123"


class TestNonStrictModeNameResolution:
    """Test non-strict mode name resolution (legacy)."""

    def test_non_strict_mode_unknown_name_returns(self) -> None:
        """Non-strict mode: unknown name returns as-is."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "123", "name": "Priority"}],
            strict=False,  # Legacy mode
        )
        gid = accessor._resolve_gid("UnknownField")
        assert gid == "UnknownField"  # Returned as-is

    def test_non_strict_mode_known_name_still_resolves(self) -> None:
        """Non-strict mode: known names still resolve to GID."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "123", "name": "Priority"}],
            strict=False,
        )
        gid = accessor._resolve_gid("Priority")
        assert gid == "123"  # Still resolves

    def test_non_strict_mode_numeric_passthrough(self) -> None:
        """Non-strict mode: numeric strings still treated as GIDs."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "123", "name": "Priority"}],
            strict=False,
        )
        gid = accessor._resolve_gid("456")
        assert gid == "456"


class TestListAvailableFields:
    """Test list_available_fields() discovery method."""

    def test_list_available_fields_empty(self) -> None:
        """Empty task returns empty list."""
        accessor = CustomFieldAccessor(data=[])
        assert accessor.list_available_fields() == []

    def test_list_available_fields_single(self) -> None:
        """Single field returned."""
        accessor = CustomFieldAccessor(data=[{"gid": "1", "name": "Priority"}])
        assert accessor.list_available_fields() == ["Priority"]

    def test_list_available_fields_multiple(self) -> None:
        """Multiple fields returned sorted."""
        accessor = CustomFieldAccessor(
            data=[
                {"gid": "1", "name": "Priority"},
                {"gid": "2", "name": "Status"},
                {"gid": "3", "name": "Budget"},
            ]
        )
        fields = accessor.list_available_fields()
        assert fields == ["Budget", "Priority", "Status"]  # Sorted

    def test_list_available_fields_no_duplicates(self) -> None:
        """Duplicate field names appear only once."""
        accessor = CustomFieldAccessor(
            data=[
                {"gid": "1", "name": "Priority"},
                {"gid": "2", "name": "Priority"},  # Duplicate
                {"gid": "3", "name": "Status"},
            ]
        )
        fields = accessor.list_available_fields()
        assert fields.count("Priority") == 1

    def test_list_available_fields_ignores_missing_names(self) -> None:
        """Fields without names are ignored."""
        accessor = CustomFieldAccessor(
            data=[
                {"gid": "1", "name": "Priority"},
                {"gid": "2"},  # No name
                {"gid": "3", "name": "Status"},
            ]
        )
        fields = accessor.list_available_fields()
        assert fields == ["Priority", "Status"]

    def test_list_available_fields_ignores_empty_names(self) -> None:
        """Empty string names are ignored."""
        accessor = CustomFieldAccessor(
            data=[
                {"gid": "1", "name": "Priority"},
                {"gid": "2", "name": ""},  # Empty name
                {"gid": "3", "name": "Status"},
            ]
        )
        fields = accessor.list_available_fields()
        assert fields == ["Priority", "Status"]

    def test_list_available_fields_case_preserved(self) -> None:
        """Original field name case is preserved."""
        accessor = CustomFieldAccessor(
            data=[
                {"gid": "1", "name": "MyPriority"},
                {"gid": "2", "name": "myStatus"},
            ]
        )
        fields = accessor.list_available_fields()
        assert "MyPriority" in fields
        assert "myStatus" in fields


class TestStrictModeIntegration:
    """Test strict mode with get/set/remove operations."""

    def test_get_with_strict_mode_unknown_name(self) -> None:
        """get() with strict mode raises on unknown name."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Priority"}],
            strict=True,
        )
        with pytest.raises(NameNotFoundError):
            accessor.get("UnknownField")

    def test_set_with_strict_mode_unknown_name(self) -> None:
        """set() with strict mode raises on unknown name."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Priority"}],
            strict=True,
        )
        with pytest.raises(NameNotFoundError):
            accessor.set("UnknownField", "High")

    def test_remove_with_strict_mode_unknown_name(self) -> None:
        """remove() with strict mode raises on unknown name."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Priority"}],
            strict=True,
        )
        with pytest.raises(NameNotFoundError):
            accessor.remove("UnknownField")

    def test_get_with_non_strict_mode_unknown_name(self) -> None:
        """get() with non-strict mode returns default for unknown name."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Priority"}],
            strict=False,
        )
        # Non-strict mode: should not raise, just return default
        result = accessor.get("UnknownField", "default_value")
        assert result == "default_value"

    def test_set_with_non_strict_mode_unknown_name(self) -> None:
        """set() with non-strict mode allows unknown names."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Priority"}],
            strict=False,
        )
        # Non-strict mode: should allow setting unknown names
        accessor.set("UnknownField", "Value")
        assert accessor.get("UnknownField") == "Value"

    def test_getitem_with_strict_mode_unknown_name(self) -> None:
        """__getitem__ with strict mode raises appropriate error."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Priority"}],
            strict=True,
        )
        # Should raise NameNotFoundError, not KeyError
        with pytest.raises(NameNotFoundError):
            _ = accessor["UnknownField"]

    def test_setitem_with_strict_mode_unknown_name(self) -> None:
        """__setitem__ with strict mode raises on unknown name."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Priority"}],
            strict=True,
        )
        with pytest.raises(NameNotFoundError):
            accessor["UnknownField"] = "Value"

    def test_delitem_with_strict_mode_unknown_name(self) -> None:
        """__delitem__ with strict mode raises on unknown name."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Priority"}],
            strict=True,
        )
        with pytest.raises(NameNotFoundError):
            del accessor["UnknownField"]


class TestFuzzyMatching:
    """Test fuzzy match suggestions."""

    def test_fuzzy_match_single_char_typo(self) -> None:
        """Single character typo suggests correct name."""
        accessor = CustomFieldAccessor(
            data=[
                {"gid": "1", "name": "Priority"},
            ],
            strict=True,
        )
        with pytest.raises(NameNotFoundError) as exc:
            accessor._resolve_gid("Pririty")  # Missing 'o'
        # Should suggest "Priority"
        error_str = str(exc.value).lower()
        assert "priority" in error_str

    def test_fuzzy_match_transposition(self) -> None:
        """Transposed characters suggest correct name."""
        accessor = CustomFieldAccessor(
            data=[
                {"gid": "1", "name": "Status"},
            ],
            strict=True,
        )
        with pytest.raises(NameNotFoundError) as exc:
            accessor._resolve_gid("Stauts")  # Transposed 'u' and 't'
        error_str = str(exc.value).lower()
        assert "status" in error_str

    def test_fuzzy_match_no_match_below_cutoff(self) -> None:
        """Very different name doesn't generate suggestion."""
        accessor = CustomFieldAccessor(
            data=[
                {"gid": "1", "name": "Priority"},
            ],
            strict=True,
        )
        with pytest.raises(NameNotFoundError) as exc:
            accessor._resolve_gid("ABCDEFGHIJ")  # Very different
        # Should not suggest anything (too different)
        error_str = str(exc.value)
        # But should show available names
        assert "Priority" in error_str

    def test_fuzzy_match_multiple_suggestions(self) -> None:
        """Multiple close matches generate multiple suggestions."""
        accessor = CustomFieldAccessor(
            data=[
                {"gid": "1", "name": "Priority"},
                {"gid": "2", "name": "PriorityLevel"},
            ],
            strict=True,
        )
        with pytest.raises(NameNotFoundError) as exc:
            accessor._resolve_gid("Priorty")  # Typo
        error_str = str(exc.value)
        # Should suggest similar names
        assert "Priority" in error_str or "priorty" in error_str.lower()

    def test_fuzzy_match_empty_field_list(self) -> None:
        """Fuzzy match with no fields available."""
        accessor = CustomFieldAccessor(
            data=[],
            strict=True,
        )
        with pytest.raises(NameNotFoundError) as exc:
            accessor._resolve_gid("AnyName")
        error_str = str(exc.value)
        assert "AnyName" in error_str


class TestStrictModeEdgeCases:
    """Test edge cases with strict mode."""

    def test_strict_mode_with_empty_data(self) -> None:
        """Strict mode with empty data raises on any lookup."""
        accessor = CustomFieldAccessor(data=[], strict=True)
        with pytest.raises(NameNotFoundError):
            accessor._resolve_gid("AnyField")

    def test_strict_mode_numeric_always_passthrough(self) -> None:
        """Strict mode: numeric GIDs always pass through without validation."""
        accessor = CustomFieldAccessor(data=[], strict=True)
        # Even with no data, numeric strings pass through
        gid = accessor._resolve_gid("999999999")
        assert gid == "999999999"

    def test_strict_mode_with_special_characters(self) -> None:
        """Strict mode: special characters in names work correctly."""
        accessor = CustomFieldAccessor(
            data=[
                {"gid": "1", "name": "Priority (High)"},
                {"gid": "2", "name": "Status/Phase"},
            ],
            strict=True,
        )
        assert accessor._resolve_gid("Priority (High)") == "1"
        assert accessor._resolve_gid("Status/Phase") == "2"

    def test_strict_mode_unicode_names(self) -> None:
        """Strict mode: unicode names work correctly."""
        accessor = CustomFieldAccessor(
            data=[
                {"gid": "1", "name": "优先级"},  # Chinese for "Priority"
            ],
            strict=True,
        )
        assert accessor._resolve_gid("优先级") == "1"

    def test_strict_mode_very_long_names(self) -> None:
        """Strict mode: very long field names work correctly."""
        long_name = "A" * 500
        accessor = CustomFieldAccessor(
            data=[
                {"gid": "1", "name": long_name},
            ],
            strict=True,
        )
        assert accessor._resolve_gid(long_name) == "1"

    def test_strict_mode_error_attribute_access(self) -> None:
        """Strict mode: error attributes are accessible."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Priority"}],
            strict=True,
        )
        try:
            accessor._resolve_gid("Unknown")
        except NameNotFoundError as e:
            assert e.resource_type == "custom_field"
            assert e.name == "Unknown"
            assert e.scope == "task"
            assert isinstance(e.suggestions, list)
            assert isinstance(e.available_names, list)


class TestMixedStrictAndNonStrictOperations:
    """Test behavior when mixing strict and non-strict accessors."""

    def test_separate_accessors_have_separate_strict_modes(self) -> None:
        """Two accessors with different strict modes operate independently."""
        data = [{"gid": "1", "name": "Priority"}]
        strict_accessor = CustomFieldAccessor(data=data, strict=True)
        non_strict_accessor = CustomFieldAccessor(data=data, strict=False)

        # Strict should raise
        with pytest.raises(NameNotFoundError):
            strict_accessor._resolve_gid("Unknown")

        # Non-strict should not raise
        result = non_strict_accessor._resolve_gid("Unknown")
        assert result == "Unknown"

    def test_strict_mode_parameter_isolation(self) -> None:
        """Strict mode parameter doesn't affect list_available_fields()."""
        data = [
            {"gid": "1", "name": "Priority"},
            {"gid": "2", "name": "Status"},
        ]
        strict = CustomFieldAccessor(data=data, strict=True)
        non_strict = CustomFieldAccessor(data=data, strict=False)

        # Both should return same available fields
        assert strict.list_available_fields() == non_strict.list_available_fields()


class TestStrictModeWithResolver:
    """Test strict mode interaction with custom resolvers."""

    def test_strict_mode_resolver_fallback(self) -> None:
        """Strict mode: resolver is tried before raising error."""

        class MockResolver:
            def resolve(self, name: str) -> str | None:
                if name == "ResolvedName":
                    return "resolved_gid"
                raise KeyError(f"Cannot resolve {name}")

        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Priority"}],
            resolver=MockResolver(),
            strict=True,
        )
        # Resolver should handle the name
        gid = accessor._resolve_gid("ResolvedName")
        assert gid == "resolved_gid"

    def test_strict_mode_resolver_exception_handled(self) -> None:
        """Strict mode: resolver exceptions are caught and handled."""

        class FailingResolver:
            def resolve(self, name: str) -> str | None:
                raise RuntimeError("Resolver failed")

        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Priority"}],
            resolver=FailingResolver(),
            strict=True,
        )
        # Should catch resolver exception and raise NameNotFoundError
        with pytest.raises(NameNotFoundError):
            accessor._resolve_gid("UnknownField")

    def test_non_strict_mode_with_resolver(self) -> None:
        """Non-strict mode: resolver tried, but doesn't prevent fallback."""

        class PartialResolver:
            def resolve(self, name: str) -> str | None:
                if name == "Resolved":
                    return "res_gid"
                raise KeyError()

        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Priority"}],
            resolver=PartialResolver(),
            strict=False,
        )
        # Known name through resolver
        assert accessor._resolve_gid("Resolved") == "res_gid"

        # Unknown name falls back to returning as-is
        assert accessor._resolve_gid("Unresolved") == "Unresolved"
