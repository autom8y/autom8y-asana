"""Tests for Task model custom fields integration.

Per Phase 3 Implementation Requirements: Custom Fields & SDK Integration.
"""

from __future__ import annotations

import pytest

from autom8_asana.models import Task
from autom8_asana.models.custom_field_accessor import CustomFieldAccessor


class TestTaskGetCustomFields:
    """Tests for Task.get_custom_fields() method."""

    def test_get_custom_fields_accessor(self) -> None:
        """get_custom_fields returns CustomFieldAccessor instance."""
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        accessor = task.get_custom_fields()
        assert isinstance(accessor, CustomFieldAccessor)

    def test_accessor_cached(self) -> None:
        """get_custom_fields returns same accessor instance (cached)."""
        task = Task(gid="123", custom_fields=[])
        accessor1 = task.get_custom_fields()
        accessor2 = task.get_custom_fields()
        assert accessor1 is accessor2

    def test_accessor_with_none_custom_fields(self) -> None:
        """get_custom_fields works when custom_fields is None."""
        task = Task(gid="123")
        accessor = task.get_custom_fields()
        assert isinstance(accessor, CustomFieldAccessor)
        assert len(accessor) == 0

    def test_accessor_get_value(self) -> None:
        """Accessor can get values from task custom_fields."""
        task = Task(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Priority", "text_value": "High"},
                {"gid": "789", "name": "MRR", "number_value": 1000.5},
            ],
        )
        accessor = task.get_custom_fields()
        assert accessor.get("Priority") == "High"
        assert accessor.get("MRR") == 1000.5

    def test_accessor_set_value(self) -> None:
        """Accessor can set values."""
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        accessor = task.get_custom_fields()
        accessor.set("Priority", "Low")
        assert accessor.get("Priority") == "Low"


class TestTaskModelDumpWithCustomFields:
    """Tests for Task.model_dump() with custom field changes."""

    def test_model_dump_includes_changes(self) -> None:
        """model_dump includes custom field modifications."""
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        accessor = task.get_custom_fields()
        accessor.set("Priority", "Low")

        data = task.model_dump()
        assert "custom_fields" in data
        assert len(data["custom_fields"]) == 1
        assert data["custom_fields"][0]["gid"] == "456"
        assert data["custom_fields"][0]["value"] == "Low"

    def test_model_dump_no_changes(self) -> None:
        """model_dump preserves original format when no accessor used."""
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        data = task.model_dump()
        # Original format preserved when no accessor used
        assert data["custom_fields"][0]["text_value"] == "High"

    def test_model_dump_no_changes_accessor_accessed(self) -> None:
        """model_dump preserves original format when accessor has no changes."""
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        # Access accessor but don't make changes
        _ = task.get_custom_fields()

        data = task.model_dump()
        # Original format preserved when accessor has no changes
        assert data["custom_fields"][0]["text_value"] == "High"

    def test_model_dump_with_added_field(self) -> None:
        """model_dump includes newly added fields."""
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        accessor = task.get_custom_fields()
        accessor.set("789", "New Value")

        data = task.model_dump()
        assert len(data["custom_fields"]) == 2
        gids = {cf["gid"] for cf in data["custom_fields"]}
        assert "456" in gids
        assert "789" in gids

    def test_model_dump_with_removal(self) -> None:
        """model_dump includes None for removed fields."""
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        accessor = task.get_custom_fields()
        accessor.remove("Priority")

        data = task.model_dump()
        assert data["custom_fields"][0]["value"] is None

    def test_model_dump_exclude_none(self) -> None:
        """model_dump with exclude_none still works correctly."""
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        accessor = task.get_custom_fields()
        accessor.set("Priority", "Low")

        data = task.model_dump(exclude_none=True)
        assert "custom_fields" in data
        assert data["custom_fields"][0]["value"] == "Low"


class TestBackwardCompatibility:
    """Tests for backward compatibility with direct custom_fields access."""

    def test_backward_compatible_direct_access(self) -> None:
        """Existing code can still access custom_fields directly."""
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        # Direct access still works
        assert task.custom_fields is not None
        assert task.custom_fields[0]["name"] == "Priority"
        assert task.custom_fields[0]["text_value"] == "High"

    def test_direct_access_is_original_data(self) -> None:
        """Direct access returns original data, not accessor format."""
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        # Use accessor to make changes
        accessor = task.get_custom_fields()
        accessor.set("Priority", "Low")

        # Direct access still returns original structure
        assert task.custom_fields[0]["text_value"] == "High"

    def test_model_validate_preserves_custom_fields(self) -> None:
        """model_validate preserves custom_fields structure."""
        data = {
            "gid": "123",
            "custom_fields": [
                {
                    "gid": "456",
                    "name": "Priority",
                    "type": "enum",
                    "enum_value": {"gid": "ev1", "name": "High"},
                }
            ],
        }
        task = Task.model_validate(data)
        assert task.custom_fields is not None
        assert task.custom_fields[0]["enum_value"]["name"] == "High"

    def test_iteration_and_len_via_accessor(self) -> None:
        """Accessor iteration and len work correctly."""
        task = Task(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "A", "text_value": "X"},
                {"gid": "2", "name": "B", "text_value": "Y"},
            ],
        )
        accessor = task.get_custom_fields()
        assert len(accessor) == 2
        names = [cf["name"] for cf in accessor]
        assert names == ["A", "B"]


class TestTaskCustomFieldsEdgeCases:
    """Edge case tests for Task custom fields."""

    def test_empty_custom_fields_list(self) -> None:
        """Task with empty custom_fields list works."""
        task = Task(gid="123", custom_fields=[])
        accessor = task.get_custom_fields()
        assert len(accessor) == 0
        assert not accessor.has_changes()

    def test_accessor_after_model_copy_deep(self) -> None:
        """Accessor behavior after deep model_copy.

        Pydantic's model_copy(deep=True) copies private attributes including
        their internal state. This means accessor modifications are preserved
        in the copy. If you need a clean copy, use model_validate on the
        original data instead.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        accessor = task.get_custom_fields()
        accessor.set("Priority", "Low")

        # Deep copy task - Pydantic copies private attributes too
        task_copy = task.model_copy(deep=True)

        # Original task should still have changes
        assert task.get_custom_fields().get("Priority") == "Low"

        # Deep copied task also has the accessor with its modifications
        copy_accessor = task_copy.get_custom_fields()
        assert copy_accessor is not accessor  # Different object
        assert copy_accessor.get("Priority") == "Low"  # But same modifications

        # To get a truly fresh copy, use model_validate on original data
        fresh_task = Task.model_validate(task.model_dump(exclude_none=True))
        fresh_accessor = fresh_task.get_custom_fields()
        # model_dump includes changes, so fresh task has accessor format
        assert len(fresh_accessor) == 1

    def test_model_dump_to_json_with_changes(self) -> None:
        """JSON serialization via model_dump works with custom field changes.

        Note: model_dump_json() does not use model_dump() internally in Pydantic v2,
        so for JSON serialization with accessor changes, use json.dumps(task.model_dump()).
        This is the pattern used by SaveSession for API payloads.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        accessor = task.get_custom_fields()
        accessor.set("Priority", "Low")

        import json

        # Use model_dump then json.dumps (pattern used by SaveSession)
        json_str = json.dumps(task.model_dump())
        parsed = json.loads(json_str)

        assert parsed["custom_fields"][0]["value"] == "Low"
