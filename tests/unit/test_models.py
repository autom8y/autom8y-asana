"""Tests for Pydantic models.

Verifies model behavior per ADR-0005 and TDD-0002:
- extra="ignore" for forward compatibility
- populate_by_name=True for field alias handling
- str_strip_whitespace=True for string normalization
- NameGid for typed resource references (per TDD-0002/ADR-0006)
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from autom8_asana.models import AsanaResource, NameGid, Task


# ---------------------------------------------------------------------------
# Test Fixtures - Realistic Asana API responses
# ---------------------------------------------------------------------------

TASK_MINIMAL: dict[str, Any] = {"gid": "1234567890"}

TASK_WITH_NAME: dict[str, Any] = {
    "gid": "1234567890",
    "name": "Test Task",
}

TASK_FULL: dict[str, Any] = {
    "gid": "1234567890",
    "resource_type": "task",
    "name": "Complete SDK Hardening",
    "notes": "Implement comprehensive test coverage for models",
    "html_notes": "<body>Implement comprehensive test coverage for models</body>",
    "completed": False,
    "completed_at": None,
    "completed_by": None,
    "due_on": "2024-12-31",
    "due_at": None,
    "start_on": "2024-12-01",
    "start_at": None,
    "assignee": {
        "gid": "987654321",
        "name": "Test User",
        "resource_type": "user",
    },
    "assignee_section": {
        "gid": "section123",
        "name": "In Progress",
        "resource_type": "section",
    },
    "assignee_status": "today",
    "projects": [
        {"gid": "proj111", "name": "SDK Development", "resource_type": "project"},
        {"gid": "proj222", "name": "Q4 Goals", "resource_type": "project"},
    ],
    "parent": None,
    "workspace": {
        "gid": "ws999",
        "name": "Engineering",
        "resource_type": "workspace",
    },
    "memberships": [
        {
            "project": {"gid": "proj111", "name": "SDK Development"},
            "section": {"gid": "sec1", "name": "To Do"},
        }
    ],
    "followers": [
        {"gid": "user1", "name": "Alice"},
        {"gid": "user2", "name": "Bob"},
    ],
    "tags": [
        {"gid": "tag1", "name": "urgent"},
        {"gid": "tag2", "name": "backend"},
    ],
    "num_subtasks": 3,
    "num_likes": 5,
    "num_hearts": 5,
    "is_rendered_as_separator": False,
    "custom_fields": [
        {
            "gid": "cf1",
            "name": "Priority",
            "type": "enum",
            "enum_value": {"gid": "ev1", "name": "High"},
        }
    ],
    "created_at": "2024-12-01T10:00:00.000Z",
    "modified_at": "2024-12-08T15:30:00.000Z",
    "created_by": {"gid": "creator123", "name": "Project Manager"},
    "approval_status": None,
    "external": {"gid": "ext1", "data": "external-reference-123"},
    "resource_subtype": "default_task",
    "permalink_url": "https://app.asana.com/0/proj111/1234567890",
    "liked": True,
    "hearted": True,
    "hearts": [{"gid": "heart1", "user": {"gid": "user1"}}],
    "likes": [{"gid": "like1", "user": {"gid": "user1"}}],
    "actual_time_minutes": 120.5,
}

TASK_WITH_UNKNOWN_FIELDS: dict[str, Any] = {
    "gid": "1234567890",
    "name": "Task with future fields",
    "completely_new_field": "some value",
    "another_unknown_field": {"nested": "data"},
    "experimental_feature_flag": True,
}

TASK_WITH_DEEPLY_NESTED_UNKNOWN: dict[str, Any] = {
    "gid": "1234567890",
    "name": "Task with nested unknown",
    "future_nested_object": {
        "level1": {
            "level2": {
                "level3": "deeply nested value",
            }
        }
    },
}


# ---------------------------------------------------------------------------
# AsanaResource Base Class Tests
# ---------------------------------------------------------------------------


class TestAsanaResourceBase:
    """Tests for AsanaResource base class."""

    def test_gid_is_required(self) -> None:
        """gid field is required - ValidationError if missing."""
        with pytest.raises(ValidationError) as exc_info:
            AsanaResource.model_validate({})

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("gid",)
        assert errors[0]["type"] == "missing"

    def test_minimal_valid_resource(self) -> None:
        """Resource with only gid is valid."""
        resource = AsanaResource.model_validate({"gid": "123"})

        assert resource.gid == "123"
        assert resource.resource_type is None

    def test_resource_type_optional(self) -> None:
        """resource_type field is optional."""
        resource = AsanaResource.model_validate({"gid": "123"})
        assert resource.resource_type is None

        resource_with_type = AsanaResource.model_validate(
            {
                "gid": "123",
                "resource_type": "custom_type",
            }
        )
        assert resource_with_type.resource_type == "custom_type"

    def test_extra_fields_ignored(self) -> None:
        """Unknown fields are silently ignored per ADR-0005."""
        resource = AsanaResource.model_validate(
            {
                "gid": "123",
                "unknown_field": "should be ignored",
                "another_unknown": {"nested": "data"},
            }
        )

        assert resource.gid == "123"
        assert not hasattr(resource, "unknown_field")
        assert not hasattr(resource, "another_unknown")

    def test_string_whitespace_stripped(self) -> None:
        """String fields have whitespace stripped (str_strip_whitespace=True)."""
        resource = AsanaResource.model_validate(
            {
                "gid": "  123  ",
                "resource_type": "  task  ",
            }
        )

        assert resource.gid == "123"
        assert resource.resource_type == "task"

    def test_model_config_settings(self) -> None:
        """Verify model_config is correctly set."""
        config = AsanaResource.model_config

        assert config.get("extra") == "ignore"
        assert config.get("populate_by_name") is True
        assert config.get("str_strip_whitespace") is True


# ---------------------------------------------------------------------------
# Task Model - Serialization/Deserialization Tests
# ---------------------------------------------------------------------------


class TestTaskSerialization:
    """Tests for Task model serialization and deserialization."""

    def test_create_from_minimal_data(self) -> None:
        """Task can be created from minimal data (just gid)."""
        task = Task.model_validate(TASK_MINIMAL)

        assert task.gid == "1234567890"
        assert task.name is None
        assert task.completed is None
        assert task.resource_type == "task"  # Default value

    def test_create_from_full_api_response(self) -> None:
        """Task can be created from full API response."""
        task = Task.model_validate(TASK_FULL)

        # Core fields
        assert task.gid == "1234567890"
        assert task.resource_type == "task"
        assert task.name == "Complete SDK Hardening"
        assert task.notes == "Implement comprehensive test coverage for models"
        assert (
            task.html_notes
            == "<body>Implement comprehensive test coverage for models</body>"
        )

        # Status fields
        assert task.completed is False
        assert task.completed_at is None
        assert task.completed_by is None

        # Due dates
        assert task.due_on == "2024-12-31"
        assert task.due_at is None
        assert task.start_on == "2024-12-01"
        assert task.start_at is None

        # Relationships - now NameGid per TDD-0002
        assert task.assignee is not None
        assert isinstance(task.assignee, NameGid)
        assert task.assignee.gid == "987654321"
        assert task.assignee.name == "Test User"
        assert task.assignee.resource_type == "user"
        assert task.assignee_status == "today"
        assert len(task.projects or []) == 2
        assert task.parent is None
        assert task.workspace is not None
        assert isinstance(task.workspace, NameGid)
        assert task.workspace.gid == "ws999"

        # Numeric fields
        assert task.num_subtasks == 3
        assert task.num_likes == 5
        assert task.num_hearts == 5

        # Metadata
        assert task.created_at == "2024-12-01T10:00:00.000Z"
        assert task.modified_at == "2024-12-08T15:30:00.000Z"
        assert task.permalink_url == "https://app.asana.com/0/proj111/1234567890"

        # Liked/hearted
        assert task.liked is True
        assert task.hearted is True
        assert task.actual_time_minutes == 120.5

    def test_model_dump_produces_dict(self) -> None:
        """model_dump() produces expected dict representation."""
        task = Task.model_validate(TASK_WITH_NAME)
        dumped = task.model_dump()

        assert isinstance(dumped, dict)
        assert dumped["gid"] == "1234567890"
        assert dumped["name"] == "Test Task"
        assert dumped["resource_type"] == "task"  # Default value included
        # Optional fields with None should be included
        assert "completed" in dumped
        assert dumped["completed"] is None

    def test_model_dump_exclude_none(self) -> None:
        """model_dump(exclude_none=True) excludes None values."""
        task = Task.model_validate(TASK_WITH_NAME)
        dumped = task.model_dump(exclude_none=True)

        assert "gid" in dumped
        assert "name" in dumped
        assert "resource_type" in dumped
        # None values should be excluded
        assert "completed" not in dumped
        assert "due_on" not in dumped

    def test_model_dump_json_produces_valid_json(self) -> None:
        """model_dump_json() produces valid JSON string."""
        task = Task.model_validate(TASK_FULL)
        json_str = task.model_dump_json()

        assert isinstance(json_str, str)
        # Should be parseable as JSON
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert parsed["gid"] == "1234567890"
        assert parsed["name"] == "Complete SDK Hardening"

    def test_model_dump_json_roundtrip(self) -> None:
        """JSON serialization roundtrip preserves data."""
        original = Task.model_validate(TASK_FULL)
        json_str = original.model_dump_json()
        parsed = json.loads(json_str)
        restored = Task.model_validate(parsed)

        assert restored.gid == original.gid
        assert restored.name == original.name
        assert restored.completed == original.completed
        assert restored.assignee == original.assignee
        assert restored.projects == original.projects


# ---------------------------------------------------------------------------
# Task Model - Unknown Fields Handling Tests (ADR-0005)
# ---------------------------------------------------------------------------


class TestUnknownFieldsHandling:
    """Tests for unknown field handling per ADR-0005 (extra='ignore')."""

    def test_unknown_fields_dont_raise_error(self) -> None:
        """Unknown fields from API don't cause ValidationError."""
        # Should not raise
        task = Task.model_validate(TASK_WITH_UNKNOWN_FIELDS)

        assert task.gid == "1234567890"
        assert task.name == "Task with future fields"

    def test_unknown_fields_silently_discarded(self) -> None:
        """Unknown fields are silently discarded, not stored."""
        task = Task.model_validate(TASK_WITH_UNKNOWN_FIELDS)

        # Unknown fields should not be accessible
        assert not hasattr(task, "completely_new_field")
        assert not hasattr(task, "another_unknown_field")
        assert not hasattr(task, "experimental_feature_flag")

    def test_deeply_nested_unknown_fields(self) -> None:
        """Deeply nested unknown fields are also handled gracefully."""
        task = Task.model_validate(TASK_WITH_DEEPLY_NESTED_UNKNOWN)

        assert task.gid == "1234567890"
        assert task.name == "Task with nested unknown"
        assert not hasattr(task, "future_nested_object")

    def test_unknown_fields_not_in_dump(self) -> None:
        """Unknown fields don't appear in model_dump() output."""
        task = Task.model_validate(TASK_WITH_UNKNOWN_FIELDS)
        dumped = task.model_dump()

        assert "completely_new_field" not in dumped
        assert "another_unknown_field" not in dumped
        assert "experimental_feature_flag" not in dumped

    def test_unknown_fields_not_in_json(self) -> None:
        """Unknown fields don't appear in model_dump_json() output."""
        task = Task.model_validate(TASK_WITH_UNKNOWN_FIELDS)
        json_str = task.model_dump_json()
        parsed = json.loads(json_str)

        assert "completely_new_field" not in parsed
        assert "another_unknown_field" not in parsed
        assert "experimental_feature_flag" not in parsed


# ---------------------------------------------------------------------------
# Task Model - Required vs Optional Field Validation Tests
# ---------------------------------------------------------------------------


class TestFieldValidation:
    """Tests for required vs optional field validation."""

    def test_gid_required(self) -> None:
        """gid is required - ValidationError if missing."""
        with pytest.raises(ValidationError) as exc_info:
            Task.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) and e["type"] == "missing" for e in errors)

    def test_gid_cannot_be_none(self) -> None:
        """gid cannot be None."""
        with pytest.raises(ValidationError) as exc_info:
            Task.model_validate({"gid": None})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)

    def test_gid_must_be_string(self) -> None:
        """gid must be a string - integers are not auto-coerced."""
        # Pydantic v2 does not auto-coerce int to str for string fields
        with pytest.raises(ValidationError) as exc_info:
            Task.model_validate({"gid": 123})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) and e["type"] == "string_type" for e in errors)

    def test_all_other_fields_optional(self) -> None:
        """All fields except gid are optional."""
        # Create task with only gid
        task = Task.model_validate({"gid": "minimal"})

        # All these should be None or their default
        assert task.name is None
        assert task.notes is None
        assert task.html_notes is None
        assert task.completed is None
        assert task.completed_at is None
        assert task.completed_by is None
        assert task.due_on is None
        assert task.due_at is None
        assert task.start_on is None
        assert task.start_at is None
        assert task.assignee is None
        assert task.assignee_section is None
        assert task.assignee_status is None
        assert task.projects is None
        assert task.parent is None
        assert task.workspace is None
        assert task.memberships is None
        assert task.followers is None
        assert task.tags is None
        assert task.num_subtasks is None
        assert task.num_hearts is None
        assert task.num_likes is None
        assert task.is_rendered_as_separator is None
        assert task.custom_fields is None
        assert task.created_at is None
        assert task.modified_at is None
        assert task.created_by is None
        assert task.approval_status is None
        assert task.external is None
        assert task.resource_subtype is None
        assert task.permalink_url is None
        assert task.liked is None
        assert task.hearted is None
        assert task.hearts is None
        assert task.likes is None
        assert task.actual_time_minutes is None

        # resource_type has a default value
        assert task.resource_type == "task"

    def test_none_values_handled_correctly(self) -> None:
        """Explicit None values are accepted for optional fields."""
        task = Task.model_validate(
            {
                "gid": "123",
                "name": None,
                "completed": None,
                "due_on": None,
                "assignee": None,
                "projects": None,
            }
        )

        assert task.gid == "123"
        assert task.name is None
        assert task.completed is None
        assert task.due_on is None
        assert task.assignee is None
        assert task.projects is None


# ---------------------------------------------------------------------------
# Task Model - Nested Object Handling Tests
# ---------------------------------------------------------------------------


class TestNestedObjectHandling:
    """Tests for nested object handling.

    Per TDD-0002/ADR-0006: Simple resource references use NameGid.
    Complex structures (memberships, custom_fields, external) remain as dicts.
    """

    def test_assignee_as_namegid(self) -> None:
        """Assignee is converted to NameGid (extra fields ignored per ADR-0005)."""
        task = Task.model_validate(
            {
                "gid": "123",
                "assignee": {
                    "gid": "user123",
                    "name": "John Doe",
                    "email": "john@example.com",  # Extra field - will be ignored
                    "resource_type": "user",
                },
            }
        )

        assert task.assignee is not None
        assert isinstance(task.assignee, NameGid)
        assert task.assignee.gid == "user123"
        assert task.assignee.name == "John Doe"
        assert task.assignee.resource_type == "user"
        # Extra fields are ignored per ADR-0005
        assert not hasattr(task.assignee, "email")

    def test_projects_as_list_of_namegid(self) -> None:
        """Projects list contains NameGid objects (extra fields ignored)."""
        task = Task.model_validate(
            {
                "gid": "123",
                "projects": [
                    {"gid": "proj1", "name": "Project A", "resource_type": "project"},
                    {
                        "gid": "proj2",
                        "name": "Project B",
                        "color": "blue",
                    },  # color ignored
                ],
            }
        )

        assert task.projects is not None
        assert len(task.projects) == 2
        assert isinstance(task.projects[0], NameGid)
        assert task.projects[0].gid == "proj1"
        assert task.projects[0].name == "Project A"
        assert isinstance(task.projects[1], NameGid)
        assert task.projects[1].gid == "proj2"
        # Extra field "color" is ignored per ADR-0005
        assert not hasattr(task.projects[1], "color")

    def test_workspace_as_namegid(self) -> None:
        """Workspace is converted to NameGid (extra fields ignored)."""
        task = Task.model_validate(
            {
                "gid": "123",
                "workspace": {
                    "gid": "ws1",
                    "name": "My Workspace",
                    "is_organization": True,  # Extra field - will be ignored
                },
            }
        )

        assert task.workspace is not None
        assert isinstance(task.workspace, NameGid)
        assert task.workspace.gid == "ws1"
        assert task.workspace.name == "My Workspace"
        # Extra field is ignored per ADR-0005
        assert not hasattr(task.workspace, "is_organization")

    def test_parent_as_namegid(self) -> None:
        """Parent is converted to NameGid for subtasks."""
        task = Task.model_validate(
            {
                "gid": "subtask1",
                "parent": {
                    "gid": "parent1",
                    "name": "Parent Task",
                    "resource_type": "task",
                },
            }
        )

        assert task.parent is not None
        assert isinstance(task.parent, NameGid)
        assert task.parent.gid == "parent1"
        assert task.parent.name == "Parent Task"

    def test_followers_as_list_of_namegid(self) -> None:
        """Followers list contains NameGid objects."""
        task = Task.model_validate(
            {
                "gid": "123",
                "followers": [
                    {"gid": "f1", "name": "Follower 1"},
                    {"gid": "f2", "name": "Follower 2"},
                ],
            }
        )

        assert task.followers is not None
        assert len(task.followers) == 2
        assert isinstance(task.followers[0], NameGid)
        assert task.followers[0].name == "Follower 1"

    def test_tags_as_list_of_namegid(self) -> None:
        """Tags list contains NameGid objects (extra fields ignored)."""
        task = Task.model_validate(
            {
                "gid": "123",
                "tags": [
                    {"gid": "tag1", "name": "urgent", "color": "red"},  # color ignored
                    {"gid": "tag2", "name": "feature"},
                ],
            }
        )

        assert task.tags is not None
        assert len(task.tags) == 2
        assert isinstance(task.tags[0], NameGid)
        assert task.tags[0].name == "urgent"
        # Extra field "color" is ignored per ADR-0005
        assert not hasattr(task.tags[0], "color")

    def test_custom_fields_list_preserved(self) -> None:
        """Custom fields list is preserved with all nested data."""
        task = Task.model_validate(
            {
                "gid": "123",
                "custom_fields": [
                    {
                        "gid": "cf1",
                        "name": "Priority",
                        "type": "enum",
                        "enum_value": {"gid": "ev1", "name": "High", "color": "red"},
                        "enum_options": [
                            {"gid": "ev1", "name": "High"},
                            {"gid": "ev2", "name": "Medium"},
                            {"gid": "ev3", "name": "Low"},
                        ],
                    },
                    {
                        "gid": "cf2",
                        "name": "Story Points",
                        "type": "number",
                        "number_value": 5,
                    },
                ],
            }
        )

        assert task.custom_fields is not None
        assert len(task.custom_fields) == 2
        assert task.custom_fields[0]["type"] == "enum"
        assert task.custom_fields[0]["enum_value"]["name"] == "High"
        assert task.custom_fields[1]["number_value"] == 5

    def test_memberships_list_preserved(self) -> None:
        """Memberships list with nested project/section is preserved."""
        task = Task.model_validate(
            {
                "gid": "123",
                "memberships": [
                    {
                        "project": {"gid": "proj1", "name": "Project A"},
                        "section": {"gid": "sec1", "name": "To Do"},
                    },
                ],
            }
        )

        assert task.memberships is not None
        assert len(task.memberships) == 1
        assert task.memberships[0]["project"]["gid"] == "proj1"
        assert task.memberships[0]["section"]["name"] == "To Do"


# ---------------------------------------------------------------------------
# Task Model - Field Alias Handling Tests (populate_by_name=True)
# ---------------------------------------------------------------------------


class TestFieldAliasHandling:
    """Tests for field alias handling (populate_by_name=True)."""

    def test_field_name_works_for_input(self) -> None:
        """Standard field names work for input."""
        task = Task.model_validate(
            {
                "gid": "123",
                "due_on": "2024-12-31",
                "start_on": "2024-12-01",
            }
        )

        assert task.due_on == "2024-12-31"
        assert task.start_on == "2024-12-01"

    def test_model_dump_uses_field_names(self) -> None:
        """model_dump() uses Python field names by default."""
        task = Task.model_validate(
            {
                "gid": "123",
                "due_on": "2024-12-31",
            }
        )

        dumped = task.model_dump()
        assert "due_on" in dumped
        assert dumped["due_on"] == "2024-12-31"

    def test_model_dump_by_alias_option(self) -> None:
        """model_dump(by_alias=True) uses alias names when defined."""
        task = Task.model_validate(
            {
                "gid": "123",
                "due_on": "2024-12-31",
            }
        )

        # Currently no aliases differ from field names, so this should work the same
        dumped_by_alias = task.model_dump(by_alias=True)
        assert "due_on" in dumped_by_alias


# ---------------------------------------------------------------------------
# Task Model - Inheritance Tests
# ---------------------------------------------------------------------------


class TestTaskInheritance:
    """Tests for Task inheritance from AsanaResource."""

    def test_task_inherits_from_asana_resource(self) -> None:
        """Task inherits from AsanaResource."""
        assert issubclass(Task, AsanaResource)

    def test_task_instance_is_asana_resource(self) -> None:
        """Task instance is also AsanaResource instance."""
        task = Task.model_validate({"gid": "123"})

        assert isinstance(task, Task)
        assert isinstance(task, AsanaResource)

    def test_task_inherits_model_config(self) -> None:
        """Task inherits model_config from AsanaResource."""
        # Check that extra="ignore" is inherited
        task_config = Task.model_config

        assert task_config.get("extra") == "ignore"
        assert task_config.get("populate_by_name") is True
        assert task_config.get("str_strip_whitespace") is True

    def test_task_has_default_resource_type(self) -> None:
        """Task has default resource_type of 'task'."""
        task = Task.model_validate({"gid": "123"})
        assert task.resource_type == "task"

    def test_task_resource_type_can_be_overridden(self) -> None:
        """Task resource_type can be overridden (for milestone, etc.)."""
        task = Task.model_validate(
            {
                "gid": "123",
                "resource_type": "task",  # Explicit
            }
        )
        assert task.resource_type == "task"

        # Could theoretically be overridden in response
        task2 = Task.model_validate(
            {
                "gid": "456",
                "resource_type": "milestone",
            }
        )
        assert task2.resource_type == "milestone"


# ---------------------------------------------------------------------------
# Task Model - Edge Cases and Special Values
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases and special values."""

    def test_empty_string_name(self) -> None:
        """Empty string name is valid."""
        task = Task.model_validate(
            {
                "gid": "123",
                "name": "",
            }
        )
        assert task.name == ""

    def test_empty_lists(self) -> None:
        """Empty lists are valid for list fields."""
        task = Task.model_validate(
            {
                "gid": "123",
                "projects": [],
                "followers": [],
                "tags": [],
                "custom_fields": [],
            }
        )

        assert task.projects == []
        assert task.followers == []
        assert task.tags == []
        assert task.custom_fields == []

    def test_boolean_fields(self) -> None:
        """Boolean fields accept True/False."""
        task_true = Task.model_validate(
            {
                "gid": "123",
                "completed": True,
                "liked": True,
                "is_rendered_as_separator": True,
            }
        )

        assert task_true.completed is True
        assert task_true.liked is True
        assert task_true.is_rendered_as_separator is True

        task_false = Task.model_validate(
            {
                "gid": "456",
                "completed": False,
                "liked": False,
                "is_rendered_as_separator": False,
            }
        )

        assert task_false.completed is False
        assert task_false.liked is False
        assert task_false.is_rendered_as_separator is False

    def test_numeric_fields(self) -> None:
        """Numeric fields accept various numeric values."""
        task = Task.model_validate(
            {
                "gid": "123",
                "num_subtasks": 0,
                "num_likes": 100,
                "num_hearts": 50,
                "actual_time_minutes": 0.0,
            }
        )

        assert task.num_subtasks == 0
        assert task.num_likes == 100
        assert task.num_hearts == 50
        assert task.actual_time_minutes == 0.0

    def test_float_actual_time(self) -> None:
        """actual_time_minutes accepts float values."""
        task = Task.model_validate(
            {
                "gid": "123",
                "actual_time_minutes": 123.456,
            }
        )

        assert task.actual_time_minutes == 123.456

    def test_large_gid(self) -> None:
        """Large GID values are handled."""
        large_gid = "1234567890123456789"
        task = Task.model_validate({"gid": large_gid})

        assert task.gid == large_gid

    def test_unicode_in_strings(self) -> None:
        """Unicode characters in string fields are preserved."""
        task = Task.model_validate(
            {
                "gid": "123",
                "name": "Task with unicode: ",
                "notes": "Notes with accents: cafe, resume, naive",
            }
        )

        assert "" in task.name
        assert "" in (task.notes or "")

    def test_very_long_notes(self) -> None:
        """Very long notes field is accepted."""
        long_notes = "A" * 10000
        task = Task.model_validate(
            {
                "gid": "123",
                "notes": long_notes,
            }
        )

        assert task.notes == long_notes
        assert len(task.notes) == 10000


# ---------------------------------------------------------------------------
# Task Model - Direct Construction Tests
# ---------------------------------------------------------------------------


class TestDirectConstruction:
    """Tests for direct Task construction (not from API response)."""

    def test_construct_with_required_only(self) -> None:
        """Task can be constructed with only required fields."""
        task = Task(gid="123")

        assert task.gid == "123"
        assert task.resource_type == "task"
        assert task.name is None

    def test_construct_with_all_fields(self) -> None:
        """Task can be constructed with all fields."""
        task = Task(
            gid="123",
            name="My Task",
            notes="Task notes",
            completed=False,
            due_on="2024-12-31",
            assignee=NameGid(gid="user1", name="Alice"),
        )

        assert task.gid == "123"
        assert task.name == "My Task"
        assert task.notes == "Task notes"
        assert task.completed is False
        assert task.due_on == "2024-12-31"
        assert task.assignee is not None
        assert isinstance(task.assignee, NameGid)
        assert task.assignee.gid == "user1"
        assert task.assignee.name == "Alice"

    def test_model_validate_dict_equivalent_to_constructor(self) -> None:
        """model_validate and constructor produce equivalent results."""
        data = {
            "gid": "123",
            "name": "Test",
            "completed": True,
        }

        from_validate = Task.model_validate(data)
        from_constructor = Task(gid="123", name="Test", completed=True)

        assert from_validate.gid == from_constructor.gid
        assert from_validate.name == from_constructor.name
        assert from_validate.completed == from_constructor.completed
