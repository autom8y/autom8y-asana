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
        # Use non-strict mode for legacy behavior (test was written pre-strict mode)
        accessor = CustomFieldAccessor(strict=False)
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
        data = [
            {
                "gid": "123",
                "name": "Status",
                "enum_value": {"gid": "456", "name": "Done"},
            }
        ]
        accessor = CustomFieldAccessor(data)
        assert accessor.get("Status") == {"gid": "456", "name": "Done"}

    def test_extract_multi_enum_values(self) -> None:
        """Extract multi_enum_values list."""
        data = [
            {
                "gid": "123",
                "name": "Tags",
                "multi_enum_values": [
                    {"gid": "a", "name": "Tag1"},
                    {"gid": "b", "name": "Tag2"},
                ],
            }
        ]
        accessor = CustomFieldAccessor(data)
        assert accessor.get("Tags") == [
            {"gid": "a", "name": "Tag1"},
            {"gid": "b", "name": "Tag2"},
        ]

    def test_extract_date_value(self) -> None:
        """Extract date_value field."""
        data = [{"gid": "123", "name": "Due", "date_value": "2024-12-31"}]
        accessor = CustomFieldAccessor(data)
        assert accessor.get("Due") == "2024-12-31"

    def test_extract_people_value(self) -> None:
        """Extract people_value list."""
        data = [
            {
                "gid": "123",
                "name": "Owner",
                "people_value": [
                    {"gid": "user1", "name": "Alice"},
                ],
            }
        ]
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
        # Use non-strict mode for legacy behavior (test was written pre-strict mode)
        accessor = CustomFieldAccessor(strict=False)
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


class TestCustomFieldAccessorToApiDict:
    """Tests for to_api_dict serialization.

    Per ADR-0056: Asana's API expects custom_fields as a dictionary
    mapping field GID to value, not an array of objects.
    """

    def test_to_api_dict_empty_when_no_changes(self) -> None:
        """to_api_dict returns empty dict when no modifications."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        result = accessor.to_api_dict()
        assert result == {}

    def test_to_api_dict_with_text_value(self) -> None:
        """to_api_dict formats text value correctly."""
        data = [{"gid": "123", "name": "Notes", "text_value": "Original"}]
        accessor = CustomFieldAccessor(data)
        accessor.set("Notes", "Updated")
        result = accessor.to_api_dict()
        assert result == {"123": "Updated"}

    def test_to_api_dict_with_number_value(self) -> None:
        """to_api_dict formats number value correctly."""
        data = [{"gid": "123", "name": "MRR", "number_value": 1000}]
        accessor = CustomFieldAccessor(data)
        accessor.set("MRR", 2500.50)
        result = accessor.to_api_dict()
        assert result == {"123": 2500.50}

    def test_to_api_dict_with_enum_value_dict(self) -> None:
        """to_api_dict extracts GID from enum_value dict."""
        data = [
            {
                "gid": "123",
                "name": "Status",
                "enum_value": {"gid": "opt1", "name": "Open"},
            }
        ]
        accessor = CustomFieldAccessor(data)
        # Setting enum as dict (common pattern)
        accessor.set("Status", {"gid": "opt2", "name": "Closed"})
        result = accessor.to_api_dict()
        # API expects just the GID
        assert result == {"123": "opt2"}

    def test_to_api_dict_with_enum_value_string(self) -> None:
        """to_api_dict passes through string GID for enum."""
        data = [
            {
                "gid": "123",
                "name": "Status",
                "enum_value": {"gid": "opt1", "name": "Open"},
            }
        ]
        accessor = CustomFieldAccessor(data)
        # Setting enum directly as GID string
        accessor.set("Status", "opt2")
        result = accessor.to_api_dict()
        assert result == {"123": "opt2"}

    def test_to_api_dict_with_multi_enum_list_of_dicts(self) -> None:
        """to_api_dict extracts GIDs from multi_enum list of dicts."""
        data = [{"gid": "123", "name": "Tags", "multi_enum_values": []}]
        accessor = CustomFieldAccessor(data)
        accessor.set(
            "Tags", [{"gid": "a", "name": "Tag1"}, {"gid": "b", "name": "Tag2"}]
        )
        result = accessor.to_api_dict()
        # API expects list of GIDs
        assert result == {"123": ["a", "b"]}

    def test_to_api_dict_with_multi_enum_list_of_strings(self) -> None:
        """to_api_dict passes through list of string GIDs."""
        data = [{"gid": "123", "name": "Tags", "multi_enum_values": []}]
        accessor = CustomFieldAccessor(data)
        accessor.set("Tags", ["a", "b", "c"])
        result = accessor.to_api_dict()
        assert result == {"123": ["a", "b", "c"]}

    def test_to_api_dict_with_people_list_of_dicts(self) -> None:
        """to_api_dict extracts GIDs from people_value list of dicts."""
        data = [{"gid": "123", "name": "Owner", "people_value": []}]
        accessor = CustomFieldAccessor(data)
        accessor.set(
            "Owner",
            [{"gid": "user1", "name": "Alice"}, {"gid": "user2", "name": "Bob"}],
        )
        result = accessor.to_api_dict()
        # API expects list of user GIDs
        assert result == {"123": ["user1", "user2"]}

    def test_to_api_dict_with_none_clears_field(self) -> None:
        """to_api_dict includes None for removed/cleared fields."""
        data = [{"gid": "123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        accessor.remove("Priority")
        result = accessor.to_api_dict()
        assert result == {"123": None}

    def test_to_api_dict_multiple_modifications(self) -> None:
        """to_api_dict includes all modified fields."""
        data = [
            {"gid": "123", "name": "Status", "text_value": "Open"},
            {"gid": "456", "name": "Priority", "text_value": "Low"},
        ]
        accessor = CustomFieldAccessor(data)
        accessor.set("Status", "Closed")
        accessor.set("Priority", "High")
        result = accessor.to_api_dict()
        assert result == {"123": "Closed", "456": "High"}

    def test_to_api_dict_only_includes_modifications(self) -> None:
        """to_api_dict only includes modified fields, not unchanged ones."""
        data = [
            {"gid": "123", "name": "Status", "text_value": "Open"},
            {"gid": "456", "name": "Priority", "text_value": "Low"},
        ]
        accessor = CustomFieldAccessor(data)
        accessor.set("Status", "Closed")
        # Priority not modified
        result = accessor.to_api_dict()
        assert result == {"123": "Closed"}
        assert "456" not in result

    def test_to_api_dict_with_new_field(self) -> None:
        """to_api_dict includes newly added fields."""
        accessor = CustomFieldAccessor()
        accessor.set("789", "New Value")
        result = accessor.to_api_dict()
        assert result == {"789": "New Value"}

    def test_to_api_dict_wraps_date_value(self) -> None:
        """to_api_dict wraps date string in required API format.

        Asana API requires date fields as {"date": "YYYY-MM-DD"}, not raw strings.
        The accessor handles this wrapping during serialization so callers can
        set date fields with plain ISO strings.
        """
        data = [{"gid": "123", "name": "Launch Date", "resource_subtype": "date"}]
        accessor = CustomFieldAccessor(data)
        accessor.set("Launch Date", "2025-12-18")
        result = accessor.to_api_dict()
        # API expects {"date": "YYYY-MM-DD"} format
        assert result == {"123": {"date": "2025-12-18"}}

    def test_to_api_dict_wraps_date_value_none_passthrough(self) -> None:
        """to_api_dict passes None through for date fields (to clear)."""
        data = [{"gid": "123", "name": "Launch Date", "resource_subtype": "date"}]
        accessor = CustomFieldAccessor(data)
        accessor.set("Launch Date", None)
        result = accessor.to_api_dict()
        # None clears the field, should not be wrapped
        assert result == {"123": None}

    def test_to_api_dict_date_wrapping_only_for_date_fields(self) -> None:
        """to_api_dict only wraps dates for date-type fields, not text."""
        data = [
            {"gid": "123", "name": "Launch Date", "resource_subtype": "date"},
            {"gid": "456", "name": "Notes", "resource_subtype": "text"},
        ]
        accessor = CustomFieldAccessor(data)
        accessor.set("Launch Date", "2025-12-18")
        accessor.set("Notes", "2025-12-18")  # Same string, but text field
        result = accessor.to_api_dict()
        # Date field wrapped, text field not wrapped
        assert result == {"123": {"date": "2025-12-18"}, "456": "2025-12-18"}


class TestCustomFieldAccessorDictSyntax:
    """Tests for dictionary-style access (__getitem__, __setitem__, __delitem__)."""

    def test_getitem_returns_existing_value(self) -> None:
        """__getitem__ returns value for existing field."""
        data = [{"gid": "cf_123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        assert accessor["Priority"] == "High"

    def test_getitem_by_gid(self) -> None:
        """__getitem__ works with GID too."""
        data = [{"gid": "cf_123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        assert accessor["cf_123"] == "High"

    def test_getitem_raises_keyerror_for_missing(self) -> None:
        """__getitem__ raises KeyError if field not found."""
        # Use non-strict mode for legacy behavior (test was written pre-strict mode)
        accessor = CustomFieldAccessor(strict=False)
        with pytest.raises(KeyError):
            _ = accessor["NonExistent"]

    def test_getitem_case_insensitive(self) -> None:
        """__getitem__ matches case-insensitively."""
        data = [{"gid": "cf_123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        assert accessor["PRIORITY"] == "High"
        assert accessor["priority"] == "High"

    def test_setitem_updates_field(self) -> None:
        """__setitem__ sets value."""
        data = [{"gid": "cf_123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        accessor["Priority"] = "Low"
        assert accessor["Priority"] == "Low"

    def test_setitem_marks_dirty(self) -> None:
        """__setitem__ marks field as modified."""
        data = [{"gid": "cf_123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        assert not accessor.has_changes()
        accessor["Priority"] = "Low"
        assert accessor.has_changes()

    def test_setitem_new_field_by_gid(self) -> None:
        """__setitem__ can add new field by GID."""
        accessor = CustomFieldAccessor()
        accessor["456"] = "New Value"
        assert accessor["456"] == "New Value"
        assert accessor.has_changes()

    def test_delitem_removes_field(self) -> None:
        """__delitem__ removes field (sets to None)."""
        data = [{"gid": "cf_123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        del accessor["Priority"]
        assert accessor["Priority"] is None
        assert accessor.has_changes()

    def test_delitem_raises_keyerror_for_missing(self) -> None:
        """__delitem__ raises KeyError if field doesn't exist."""
        # Use non-strict mode for legacy behavior (test was written pre-strict mode)
        accessor = CustomFieldAccessor(strict=False)
        with pytest.raises(KeyError):
            del accessor["NonExistent"]

    def test_delitem_by_gid(self) -> None:
        """__delitem__ works with GID."""
        data = [{"gid": "cf_123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)
        del accessor["cf_123"]
        assert accessor["cf_123"] is None

    def test_dict_syntax_preserves_types(self) -> None:
        """Dictionary syntax preserves field types."""
        # Text field
        accessor = CustomFieldAccessor(
            [{"gid": "cf_text", "name": "Category", "text_value": "Internal"}]
        )
        assert accessor["Category"] == "Internal"
        assert isinstance(accessor["Category"], str)

        # Number field
        accessor = CustomFieldAccessor(
            [{"gid": "cf_num", "name": "MRR", "number_value": 1000.50}]
        )
        assert accessor["MRR"] == 1000.50
        assert isinstance(accessor["MRR"], (int, float))

        # Enum field
        accessor = CustomFieldAccessor(
            [
                {
                    "gid": "cf_enum",
                    "name": "Status",
                    "enum_value": {"gid": "e_123", "name": "Active"},
                }
            ]
        )
        result = accessor["Status"]
        assert isinstance(result, dict)
        assert result.get("gid") == "e_123"

    def test_dict_syntax_with_modified_values(self) -> None:
        """Dictionary syntax works with modified values."""
        data = [{"gid": "cf_123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)

        # Set via dict syntax
        accessor["Priority"] = "Medium"

        # Get via dict syntax
        assert accessor["Priority"] == "Medium"

        # Get via old method syntax (same value)
        assert accessor.get("Priority") == "Medium"

    def test_mixed_old_and_new_syntax(self) -> None:
        """Can mix old .get()/.set() with new [] syntax."""
        data = [{"gid": "cf_123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)

        # Old syntax set
        accessor.set("Priority", "Low")

        # New syntax get
        assert accessor["Priority"] == "Low"

        # New syntax set
        accessor["Priority"] = "Urgent"

        # Old syntax get (same value)
        assert accessor.get("Priority") == "Urgent"

    def test_dict_syntax_in_to_api_dict(self) -> None:
        """Changes via __setitem__ are included in to_api_dict()."""
        data = [{"gid": "cf_123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)

        # Modify via dict syntax
        accessor["Priority"] = "Urgent"

        # Verify in API dict
        api_dict = accessor.to_api_dict()
        assert api_dict == {"cf_123": "Urgent"}

    def test_dict_syntax_in_to_list(self) -> None:
        """Changes via __setitem__ are included in to_list()."""
        data = [{"gid": "cf_123", "name": "Priority", "text_value": "High"}]
        accessor = CustomFieldAccessor(data)

        # Modify via dict syntax
        accessor["Priority"] = "Low"

        # Verify in list
        result = accessor.to_list()
        assert result[0]["value"] == "Low"

    def test_multiple_dict_operations(self) -> None:
        """Multiple dictionary operations work together."""
        data = [
            {"gid": "cf_1", "name": "Priority", "text_value": "High"},
            {"gid": "cf_2", "name": "Status", "text_value": "Open"},
        ]
        accessor = CustomFieldAccessor(data)

        # Multiple sets
        accessor["Priority"] = "Low"
        accessor["Status"] = "Closed"

        # Multiple gets
        assert accessor["Priority"] == "Low"
        assert accessor["Status"] == "Closed"

        # Delete one
        del accessor["Priority"]

        # Verify state
        assert accessor["Priority"] is None
        assert accessor["Status"] == "Closed"
        assert accessor.has_changes()


class TestFormatValueForApi:
    """Tests for _format_value_for_api internal method.

    These tests ensure proper value formatting for all Asana custom field types.
    """

    def test_format_none(self) -> None:
        """None values pass through."""
        accessor = CustomFieldAccessor()
        assert accessor._format_value_for_api(None) is None

    def test_format_string(self) -> None:
        """String values pass through."""
        accessor = CustomFieldAccessor()
        assert accessor._format_value_for_api("text") == "text"

    def test_format_number_int(self) -> None:
        """Integer values pass through."""
        accessor = CustomFieldAccessor()
        assert accessor._format_value_for_api(42) == 42

    def test_format_number_float(self) -> None:
        """Float values pass through."""
        accessor = CustomFieldAccessor()
        assert accessor._format_value_for_api(3.14159) == 3.14159

    def test_format_dict_with_gid(self) -> None:
        """Dict with gid extracts the GID."""
        accessor = CustomFieldAccessor()
        result = accessor._format_value_for_api({"gid": "123", "name": "Option"})
        assert result == "123"

    def test_format_dict_without_gid(self) -> None:
        """Dict without gid passes through (edge case)."""
        accessor = CustomFieldAccessor()
        result = accessor._format_value_for_api({"name": "No GID"})
        assert result == {"name": "No GID"}

    def test_format_list_of_dicts_with_gid(self) -> None:
        """List of dicts with gid extracts GIDs."""
        accessor = CustomFieldAccessor()
        result = accessor._format_value_for_api(
            [
                {"gid": "a", "name": "A"},
                {"gid": "b", "name": "B"},
            ]
        )
        assert result == ["a", "b"]

    def test_format_list_of_strings(self) -> None:
        """List of strings passes through."""
        accessor = CustomFieldAccessor()
        result = accessor._format_value_for_api(["a", "b", "c"])
        assert result == ["a", "b", "c"]

    def test_format_list_mixed_types(self) -> None:
        """List with mixed types handles each appropriately."""
        accessor = CustomFieldAccessor()
        result = accessor._format_value_for_api(
            [
                {"gid": "a", "name": "A"},
                "b",
                123,
            ]
        )
        assert result == ["a", "b", 123]

    def test_format_object_with_gid_attribute(self) -> None:
        """Object with gid attribute extracts the gid."""

        class MockModel:
            def __init__(self, gid: str):
                self.gid = gid

        accessor = CustomFieldAccessor()
        model = MockModel("model_123")
        result = accessor._format_value_for_api(model)
        assert result == "model_123"

    def test_format_list_of_objects_with_gid(self) -> None:
        """List of objects with gid attribute extracts gids."""

        class MockModel:
            def __init__(self, gid: str):
                self.gid = gid

        accessor = CustomFieldAccessor()
        result = accessor._format_value_for_api([MockModel("a"), MockModel("b")])
        assert result == ["a", "b"]

    def test_format_empty_list(self) -> None:
        """Empty list passes through."""
        accessor = CustomFieldAccessor()
        assert accessor._format_value_for_api([]) == []
