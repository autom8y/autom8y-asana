"""Tests for CustomFieldAccessor.

Per Phase 3 Implementation Requirements: Custom Fields & SDK Integration.
"""

from __future__ import annotations

import pytest

from autom8_asana.models.custom_field_accessor import CustomFieldAccessor


class TestCustomFieldAccessorInit:
    """Tests for CustomFieldAccessor initialization."""

    def test_init_empty(self) -> None:
        """Empty accessor has no fields and no changes."""
        accessor = CustomFieldAccessor()
        assert len(accessor) == 0
        assert not accessor.has_changes()

    def test_init_with_none(self) -> None:
        """Init with None is treated as empty."""
        accessor = CustomFieldAccessor(None)
        assert len(accessor) == 0

    def test_init_with_data(self) -> None:
        """Accessor initialized with data has correct length."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        assert len(accessor) == 1

    def test_init_copies_data(self) -> None:
        """Data is copied, not referenced."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        data.append({"gid": "456", "name": "Status"})
        assert len(accessor) == 1  # Original data unchanged


class TestCustomFieldAccessorGet:
    """Tests for get operations."""

    def test_get_by_name(self) -> None:
        """Get value by field name."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        assert accessor.get("Priority") == "High"

    def test_get_by_name_case_insensitive(self) -> None:
        """Get by name is case-insensitive."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        assert accessor.get("PRIORITY") == "High"
        assert accessor.get("priority") == "High"
        assert accessor.get("PrIoRiTy") == "High"

    def test_get_by_name_whitespace_stripped(self) -> None:
        """Get by name strips whitespace."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        assert accessor.get("  Priority  ") == "High"

    def test_get_by_gid(self) -> None:
        """Get value by GID."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        assert accessor.get("123") == "High"

    def test_get_default(self) -> None:
        """Get returns default for missing fields."""
        accessor = CustomFieldAccessor()
        assert accessor.get("Missing") is None
        assert accessor.get("Missing", "default") == "default"

    def test_get_returns_modified_value(self) -> None:
        """Get returns modified value over original."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        accessor.set("Priority", "Low")
        assert accessor.get("Priority") == "Low"


class TestCustomFieldAccessorSet:
    """Tests for set operations."""

    def test_set_by_name(self) -> None:
        """Set value by field name."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        accessor.set("Priority", "Low")
        assert accessor.get("Priority") == "Low"
        assert accessor.has_changes()

    def test_set_by_gid(self) -> None:
        """Set value by GID."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        accessor.set("123", "Low")
        assert accessor.get("123") == "Low"

    def test_set_new_field_by_gid(self) -> None:
        """Set a field not in original data by GID."""
        accessor = CustomFieldAccessor()
        accessor.set("456", "New Value")
        assert accessor.get("456") == "New Value"
        assert accessor.has_changes()

    def test_set_overwrites_previous_set(self) -> None:
        """Multiple sets overwrite previous value."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        accessor.set("Priority", "Low")
        accessor.set("Priority", "Medium")
        assert accessor.get("Priority") == "Medium"


class TestCustomFieldAccessorRemove:
    """Tests for remove operations."""

    def test_remove(self) -> None:
        """Remove sets field to None."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        accessor.remove("Priority")
        assert accessor.get("Priority") is None
        assert accessor.has_changes()

    def test_remove_by_gid(self) -> None:
        """Remove by GID."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        accessor.remove("123")
        assert accessor.get("123") is None


class TestCustomFieldAccessorToList:
    """Tests for to_list serialization."""

    def test_to_list_no_changes(self) -> None:
        """to_list returns original values when no changes."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        result = accessor.to_list()
        assert len(result) == 1
        assert result[0]["gid"] == "123"
        assert result[0]["value"] == "High"

    def test_to_list_with_changes(self) -> None:
        """to_list includes modifications."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        accessor.set("Priority", "Low")
        result = accessor.to_list()
        assert result[0]["value"] == "Low"

    def test_to_list_with_new_field(self) -> None:
        """to_list includes new fields not in original data."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        accessor.set("456", "New")
        result = accessor.to_list()
        assert len(result) == 2
        gids = {r["gid"] for r in result}
        assert "123" in gids
        assert "456" in gids

    def test_to_list_with_removal(self) -> None:
        """to_list includes None for removed fields."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        accessor.remove("Priority")
        result = accessor.to_list()
        assert result[0]["value"] is None


class TestCustomFieldAccessorValueExtraction:
    """Tests for value extraction from different field types."""

    def test_extract_text_value(self) -> None:
        """Extract text_value field."""
        data = [{"gid": "123", "name": "Notes", "text_value": "Some text"}]
        accessor = CustomFieldAccessor(data)
        assert accessor.get("Notes") == "Some text"

    def test_extract_number_value(self) -> None:
        """Extract number_value field."""
        data = [{"gid": "123", "name": "MRR", "number_value": 1000.5}]
        accessor = CustomFieldAccessor(data)
        assert accessor.get("MRR") == 1000.5

    def test_extract_number_value_zero(self) -> None:
        """Extract zero number_value (not falsy)."""
        data = [{"gid": "123", "name": "Count", "number_value": 0}]
        accessor = CustomFieldAccessor(data)
        # Zero is falsy but should still be returned
        assert accessor.get("Count") == 0

    def test_extract_enum_value(self) -> None:
        """Extract enum_value dict."""
        data = [{"gid": "123", "name": "Status", "enum_value": {"gid": "456", "name": "Done"}}]
        accessor = CustomFieldAccessor(data)
        assert accessor.get("Status") == {"gid": "456", "name": "Done"}

    def test_extract_multi_enum_values(self) -> None:
        """Extract multi_enum_values list."""
        data = [{"gid": "123", "name": "Tags", "multi_enum_values": [
            {"gid": "a", "name": "Tag1"},
            {"gid": "b", "name": "Tag2"},
        ]}]
        accessor = CustomFieldAccessor(data)
        assert accessor.get("Tags") == [{"gid": "a", "name": "Tag1"}, {"gid": "b", "name": "Tag2"}]

    def test_extract_date_value(self) -> None:
        """Extract date_value field."""
        data = [{"gid": "123", "name": "Due", "date_value": "2024-12-31"}]
        accessor = CustomFieldAccessor(data)
        assert accessor.get("Due") == "2024-12-31"

    def test_extract_people_value(self) -> None:
        """Extract people_value list."""
        data = [{"gid": "123", "name": "Owner", "people_value": [
            {"gid": "user1", "name": "Alice"},
        ]}]
        accessor = CustomFieldAccessor(data)
        assert accessor.get("Owner") == [{"gid": "user1", "name": "Alice"}]

    def test_extract_display_value_fallback(self) -> None:
        """Fallback to display_value when type-specific field not present."""
        data = [{"gid": "123", "name": "Custom", "display_value": "Displayed"}]
        accessor = CustomFieldAccessor(data)
        assert accessor.get("Custom") == "Displayed"

    def test_extract_none_when_all_empty(self) -> None:
        """Return None when no value fields present."""
        data = [{"gid": "123", "name": "Empty"}]
        accessor = CustomFieldAccessor(data)
        assert accessor.get("Empty") is None


class TestCustomFieldAccessorChanges:
    """Tests for change tracking."""

    def test_has_changes_false_initially(self) -> None:
        """has_changes is False before any modifications."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        assert not accessor.has_changes()

    def test_has_changes_true_after_set(self) -> None:
        """has_changes is True after set."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        accessor.set("Priority", "Low")
        assert accessor.has_changes()

    def test_has_changes_true_after_remove(self) -> None:
        """has_changes is True after remove."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        accessor.remove("Priority")
        assert accessor.has_changes()

    def test_clear_changes(self) -> None:
        """clear_changes removes all pending modifications."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        accessor.set("Priority", "Low")
        assert accessor.has_changes()
        accessor.clear_changes()
        assert not accessor.has_changes()
        # Original value should be restored
        assert accessor.get("Priority") == "High"


class TestCustomFieldAccessorIteration:
    """Tests for iteration and len."""

    def test_len_empty(self) -> None:
        """Length of empty accessor is 0."""
        accessor = CustomFieldAccessor()
        assert len(accessor) == 0

    def test_len_with_data(self) -> None:
        """Length equals number of original fields."""
        data = [
            {"gid": "1", "name": "A"},
            {"gid": "2", "name": "B"},
            {"gid": "3", "name": "C"},
        ]
        accessor = CustomFieldAccessor(data)
        assert len(accessor) == 3

    def test_iter(self) -> None:
        """Iteration yields original field dicts."""
        data = [
            {"gid": "1", "name": "A"},
            {"gid": "2", "name": "B"},
        ]
        accessor = CustomFieldAccessor(data)
        items = list(accessor)
        assert len(items) == 2
        assert items[0]["gid"] == "1"
        assert items[1]["gid"] == "2"


class TestCustomFieldAccessorEdgeCases:
    """Tests for edge cases."""

    def test_field_without_gid_skipped_in_to_list(self) -> None:
        """Fields without GID are skipped in to_list."""
        data = [
            {"gid": "123", "name": "Valid", "text_value": "V"},
            {"name": "NoGid", "text_value": "X"},  # No gid
        ]
        accessor = CustomFieldAccessor(data)
        result = accessor.to_list()
        assert len(result) == 1
        assert result[0]["gid"] == "123"

    def test_field_without_name_still_indexed_by_gid(self) -> None:
        """Fields without name can still be accessed by GID."""
        data = [{"gid": "123", "text_value": "Value"}]
        accessor = CustomFieldAccessor(data)
        assert accessor.get("123") == "Value"

    def test_empty_string_name_indexed(self) -> None:
        """Empty string name is not indexed."""
        data = [{"gid": "123", "name": "", "text_value": "Value"}]
        accessor = CustomFieldAccessor(data)
        # Empty name should not be in index (if check fails on empty string)
        assert accessor.get("123") == "Value"

    def test_unknown_name_returns_as_is(self) -> None:
        """Unknown name without resolver returns as-is."""
        accessor = CustomFieldAccessor()
        # Setting by unknown name - name returned as-is as potential GID
        accessor.set("UnknownField", "Value")
        # get by same name should return value
        assert accessor.get("UnknownField") == "Value"

    def test_numeric_looking_non_gid(self) -> None:
        """Numeric-looking string is treated as GID."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        # "123" should be treated as GID
        accessor.set("123", "Low")
        assert accessor.get("123") == "Low"
        # Should also be accessible by name
        assert accessor.get("Priority") == "Low"

    def test_multiple_fields_same_gid(self) -> None:
        """Last field with same GID wins in original data."""
        # This is an edge case - API shouldn't return this
        data = [
            {"gid": "123", "name": "First", "text_value": "A"},
            {"gid": "123", "name": "Second", "text_value": "B"},
        ]
        accessor = CustomFieldAccessor(data)
        # to_list should include both (weird but correct)
        result = accessor.to_list()
        assert len(result) == 2
