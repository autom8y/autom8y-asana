"""Tests for Pydantic models.

Verifies model behavior per ADR-0005 and TDD-0002:
- extra="ignore" for forward compatibility
- populate_by_name=True for field alias handling
- str_strip_whitespace=True for string normalization
- NameGid for typed resource references (per TDD-0002/ADR-0006)
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from autom8_asana.models import AsanaResource, NameGid, PageIterator, Task

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
    "likes": [{"gid": "like1", "user": {"gid": "user1"}}],
    "actual_time_minutes": 120.5,
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
        assert task.html_notes == "<body>Implement comprehensive test coverage for models</body>"

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

        # Metadata
        assert task.created_at == "2024-12-01T10:00:00.000Z"
        assert task.modified_at == "2024-12-08T15:30:00.000Z"
        assert task.permalink_url == "https://app.asana.com/0/proj111/1234567890"

        # Liked status
        assert task.liked is True
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


# ---------------------------------------------------------------------------
# NameGid Validation Edge Cases (merged from test_phase2a_adversarial.py)
# ---------------------------------------------------------------------------


class TestNameGidValidationEdgeCases:
    """Adversarial validation edge cases for NameGid."""

    def test_empty_gid_string(self) -> None:
        """Empty string gid is accepted (documents gap: may never be valid from API)."""
        ref = NameGid(gid="")
        assert ref.gid == ""

    def test_gid_with_leading_trailing_whitespace(self) -> None:
        """Whitespace around valid gid is stripped."""
        ref = NameGid(gid="  12345  ")
        assert ref.gid == "12345"

    def test_gid_type_coercion_integer_fails(self) -> None:
        """Integer gid should fail validation (Pydantic v2 strict string)."""
        with pytest.raises(ValidationError) as exc_info:
            NameGid(gid=12345)  # type: ignore[arg-type]

        errors = exc_info.value.errors()
        assert any(e["type"] == "string_type" for e in errors)

    def test_gid_type_coercion_float_fails(self) -> None:
        """Float gid should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            NameGid(gid=123.45)  # type: ignore[arg-type]

        errors = exc_info.value.errors()
        assert any(e["type"] == "string_type" for e in errors)

    def test_name_whitespace_only_stripped(self) -> None:
        """Name with only whitespace is stripped to empty string."""
        ref = NameGid(gid="123", name="   ")
        assert ref.name == ""

    def test_name_with_newlines(self) -> None:
        """Name with newlines is preserved."""
        ref = NameGid(gid="123", name="Line1\nLine2\nLine3")
        assert "\n" in (ref.name or "")

    def test_name_with_tabs(self) -> None:
        """Name with tabs is preserved."""
        ref = NameGid(gid="123", name="Col1\tCol2")
        assert "\t" in (ref.name or "")


# ---------------------------------------------------------------------------
# NameGid Hashing and Equality (merged from test_phase2a_adversarial.py)
# ---------------------------------------------------------------------------


class TestNameGidHashingEquality:
    """Edge cases for NameGid hashing and equality (equality is gid-based)."""

    def test_hash_consistency_for_equal_objects(self) -> None:
        """Equal objects must have equal hashes."""
        ref1 = NameGid(gid="123", name="Alice")
        ref2 = NameGid(gid="123", name="Bob")  # Same gid, different name

        assert ref1 == ref2
        assert hash(ref1) == hash(ref2)

    def test_hash_stability(self) -> None:
        """Hash of same object is stable across multiple calls."""
        ref = NameGid(gid="123", name="Test")
        h1 = hash(ref)
        h2 = hash(ref)
        h3 = hash(ref)

        assert h1 == h2 == h3

    def test_set_membership_with_different_names(self) -> None:
        """Set membership is based on gid, not name."""
        s = {NameGid(gid="123", name="Alice")}

        # Same gid, different name - should be "in" the set
        assert NameGid(gid="123", name="Bob") in s
        # Different gid - should not be in the set
        assert NameGid(gid="456", name="Alice") not in s

    def test_dict_key_lookup(self) -> None:
        """Dict key lookup is based on gid."""
        d = {NameGid(gid="123", name="Key1"): "value1"}

        # Same gid, different name should find the value
        assert d[NameGid(gid="123", name="Different")] == "value1"

    def test_equality_with_non_namegid_returns_false(self) -> None:
        """Equality with non-NameGid types returns False."""
        ref = NameGid(gid="123")

        assert ref != "123"
        assert ref != {"gid": "123"}
        assert ref != 123
        assert ref != None  # noqa: E711

    def test_inequality_operator(self) -> None:
        """!= operator works correctly."""
        ref1 = NameGid(gid="123")
        ref2 = NameGid(gid="456")
        ref3 = NameGid(gid="123")

        assert ref1 != ref2
        assert ref1 == ref3


# ---------------------------------------------------------------------------
# PageIterator Exception Handling (merged from test_phase2a_adversarial.py)
# ---------------------------------------------------------------------------


class TestPageIteratorExceptionHandling:
    """Exception propagation tests for PageIterator."""

    async def test_fetch_raises_on_first_page(self) -> None:
        """fetch_page raises exception on first call propagates out."""

        async def fetch_page(offset: str | None) -> tuple[list[str], str | None]:
            raise ValueError("Network error")

        iterator = PageIterator(fetch_page)

        with pytest.raises(ValueError, match="Network error"):
            await iterator.collect()

    async def test_fetch_raises_on_second_page(self) -> None:
        """Exception on second page propagates after first page succeeds."""
        call_count = [0]

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            call_count[0] += 1
            if call_count[0] == 1:
                return [1, 2], "offset1"
            raise ConnectionError("Connection lost")

        iterator = PageIterator(fetch_page)

        with pytest.raises(ConnectionError, match="Connection lost"):
            await iterator.collect()

        assert call_count[0] == 2

    async def test_fetch_raises_during_async_for_iteration(self) -> None:
        """Exception during async for loop propagates and yields first page items."""
        call_count = [0]

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            call_count[0] += 1
            if call_count[0] == 2:
                raise RuntimeError("Mid-iteration failure")
            return [1, 2, 3], "next"

        iterator = PageIterator(fetch_page)
        items = []

        with pytest.raises(RuntimeError, match="Mid-iteration failure"):
            async for item in iterator:
                items.append(item)

        assert items == [1, 2, 3]


# ---------------------------------------------------------------------------
# PageIterator State Management (merged from test_phase2a_adversarial.py)
# ---------------------------------------------------------------------------


class TestPageIteratorStateManagement:
    """State management after exhaustion and partial iteration."""

    async def test_collect_multiple_times_exhausts_iterator(self) -> None:
        """Second collect() returns empty because iterator is exhausted.

        FINDING: This is expected behavior but worth documenting.
        """

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            return [1, 2, 3], None

        iterator = PageIterator(fetch_page)

        result1 = await iterator.collect()
        assert result1 == [1, 2, 3]

        result2 = await iterator.collect()
        assert result2 == []  # Empty because exhausted

    async def test_first_then_collect_returns_remaining(self) -> None:
        """Calling first() then collect() returns only remaining items."""

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            return [1, 2, 3], None

        iterator = PageIterator(fetch_page)

        first = await iterator.first()
        assert first == 1

        remaining = await iterator.collect()
        assert remaining == [2, 3]

    async def test_iteration_after_exhaustion(self) -> None:
        """Iterating after exhaustion yields nothing."""

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            return [1], None

        iterator = PageIterator(fetch_page)

        await iterator.collect()

        items = []
        async for item in iterator:
            items.append(item)

        assert items == []


# ---------------------------------------------------------------------------
# PageIterator Memory Efficiency (merged from test_phase2a_adversarial.py)
# ---------------------------------------------------------------------------


class TestPageIteratorMemoryEfficiency:
    """Memory efficiency tests for PageIterator."""

    async def test_large_result_set_streaming(self) -> None:
        """take(50) fetches only 1 page even with 10 pages available."""
        pages_fetched = []

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            page_num = len(pages_fetched)
            pages_fetched.append(page_num)

            if page_num < 10:
                return list(range(page_num * 100, (page_num + 1) * 100)), f"page{page_num + 1}"
            return [], None

        iterator = PageIterator(fetch_page)

        items = await iterator.take(50)

        assert len(items) == 50
        # Should only have fetched 1 page (first page has 100 items)
        assert len(pages_fetched) == 1

    async def test_buffer_cleared_after_consumption(self) -> None:
        """Buffer is empty after all items are consumed."""

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            return list(range(100)), None

        iterator = PageIterator(fetch_page)

        count = 0
        async for _ in iterator:
            count += 1
            if count == 100:
                assert iterator._buffer == []

        assert count == 100


# ---------------------------------------------------------------------------
# TasksClient.list_async() Filter Parameter Tests
# (merged from test_phase2a_adversarial.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_http_for_tasks() -> AsyncMock:
    """Create mock HTTP client for tasks tests."""
    mock = AsyncMock()
    mock.get_paginated = AsyncMock(return_value=([], None))
    return mock


@pytest.fixture
def tasks_client_local(mock_http_for_tasks: AsyncMock) -> Any:
    """Create TasksClient with mocked HTTP."""
    from autom8_asana.clients.tasks import TasksClient
    from autom8_asana.config import AsanaConfig

    class MockAuthProvider:
        def get_secret(self, key: str) -> str:
            return "token"

    return TasksClient(
        http=mock_http_for_tasks,
        config=AsanaConfig(),
        auth_provider=MockAuthProvider(),
    )


class TestListAsyncFilterParameters:
    """Tests for TasksClient.list_async() filter parameters."""

    async def test_project_filter(
        self, tasks_client_local: Any, mock_http_for_tasks: AsyncMock
    ) -> None:
        """Project filter is passed correctly."""
        iterator = tasks_client_local.list_async(project="proj123")
        await iterator.collect()

        params = mock_http_for_tasks.get_paginated.call_args[1]["params"]
        assert params.get("project") == "proj123"

    async def test_assignee_filter(
        self, tasks_client_local: Any, mock_http_for_tasks: AsyncMock
    ) -> None:
        """Assignee and workspace filters are passed correctly."""
        iterator = tasks_client_local.list_async(assignee="me", workspace="ws123")
        await iterator.collect()

        params = mock_http_for_tasks.get_paginated.call_args[1]["params"]
        assert params.get("assignee") == "me"
        assert params.get("workspace") == "ws123"

    async def test_opt_fields_joined(
        self, tasks_client_local: Any, mock_http_for_tasks: AsyncMock
    ) -> None:
        """opt_fields list is joined with commas."""
        iterator = tasks_client_local.list_async(
            project="proj1",
            opt_fields=["name", "completed", "due_on"],
        )
        await iterator.collect()

        params = mock_http_for_tasks.get_paginated.call_args[1]["params"]
        opt_fields = set(params.get("opt_fields", "").split(","))
        assert {"name", "completed", "due_on"}.issubset(opt_fields)

    async def test_limit_capped_at_100(
        self, tasks_client_local: Any, mock_http_for_tasks: AsyncMock
    ) -> None:
        """Limit is capped at 100 (Asana max)."""
        iterator = tasks_client_local.list_async(project="proj1", limit=200)
        await iterator.collect()

        params = mock_http_for_tasks.get_paginated.call_args[1]["params"]
        assert params.get("limit") == 100

    async def test_empty_project_filter_not_included(
        self, tasks_client_local: Any, mock_http_for_tasks: AsyncMock
    ) -> None:
        """Empty string project filter is not included in params."""
        iterator = tasks_client_local.list_async(project="", workspace="ws123")
        await iterator.collect()

        params = mock_http_for_tasks.get_paginated.call_args[1]["params"]
        assert "project" not in params

    async def test_all_filters_combined(
        self, tasks_client_local: Any, mock_http_for_tasks: AsyncMock
    ) -> None:
        """All filters can be combined in a single call."""
        iterator = tasks_client_local.list_async(
            project="proj1",
            section="sec1",
            assignee="user1",
            workspace="ws1",
            completed_since="2024-01-01T00:00:00Z",
            modified_since="2024-06-01T00:00:00Z",
            opt_fields=["name"],
            limit=50,
        )
        await iterator.collect()

        params = mock_http_for_tasks.get_paginated.call_args[1]["params"]
        assert params["project"] == "proj1"
        assert params["section"] == "sec1"
        assert params["assignee"] == "user1"
        assert params["workspace"] == "ws1"
        assert params["completed_since"] == "2024-01-01T00:00:00Z"
        assert params["modified_since"] == "2024-06-01T00:00:00Z"
        assert "name" in params["opt_fields"]
        assert params["limit"] == 50


class TestListAsyncPagination:
    """Tests for pagination behavior of TasksClient.list_async()."""

    async def test_pagination_offset_passed(
        self, tasks_client_local: Any, mock_http_for_tasks: AsyncMock
    ) -> None:
        """Pagination offset is passed correctly on subsequent pages."""
        mock_http_for_tasks.get_paginated.side_effect = [
            ([{"gid": "1", "name": "Task 1"}], "offset_abc"),
            ([{"gid": "2", "name": "Task 2"}], None),
        ]

        iterator = tasks_client_local.list_async(project="proj1")
        tasks = await iterator.collect()

        assert len(tasks) == 2
        assert mock_http_for_tasks.get_paginated.call_count == 2

        second_call_params = mock_http_for_tasks.get_paginated.call_args_list[1][1]["params"]
        assert second_call_params.get("offset") == "offset_abc"

    async def test_empty_page_stops_iteration(
        self, tasks_client_local: Any, mock_http_for_tasks: AsyncMock
    ) -> None:
        """Empty page with no offset stops iteration."""
        mock_http_for_tasks.get_paginated.return_value = ([], None)

        iterator = tasks_client_local.list_async(project="proj1")
        tasks = await iterator.collect()

        assert tasks == []
        assert mock_http_for_tasks.get_paginated.call_count == 1


class TestListAsyncErrorHandling:
    """Error handling tests for TasksClient.list_async()."""

    async def test_network_error_during_pagination(
        self, tasks_client_local: Any, mock_http_for_tasks: AsyncMock
    ) -> None:
        """Network error mid-pagination is propagated."""
        from autom8_asana.errors import AsanaError

        mock_http_for_tasks.get_paginated.side_effect = [
            ([{"gid": "1"}], "offset1"),
            AsanaError("Network error"),
        ]

        iterator = tasks_client_local.list_async(project="proj1")

        with pytest.raises(AsanaError, match="Network error"):
            await iterator.collect()

    async def test_invalid_task_data_fails_validation(
        self, tasks_client_local: Any, mock_http_for_tasks: AsyncMock
    ) -> None:
        """Invalid task data (missing gid) fails Pydantic validation."""
        mock_http_for_tasks.get_paginated.return_value = (
            [{"name": "No GID Task"}],
            None,
        )

        iterator = tasks_client_local.list_async(project="proj1")

        with pytest.raises(ValidationError):
            await iterator.collect()


# ---------------------------------------------------------------------------
# End-to-End Scenarios (merged from test_phase2a_adversarial.py)
# ---------------------------------------------------------------------------


class TestEndToEndScenarios:
    """End-to-end scenarios combining models and pagination."""

    async def test_iterate_tasks_access_namegid_fields(self) -> None:
        """Iterate tasks from PageIterator and access NameGid fields."""
        task_data = [
            {
                "gid": "task1",
                "name": "Task 1",
                "assignee": {"gid": "user1", "name": "Alice"},
                "projects": [{"gid": "proj1", "name": "Project A"}],
            },
            {
                "gid": "task2",
                "name": "Task 2",
                "assignee": {"gid": "user2", "name": "Bob"},
                "projects": [],
            },
        ]

        async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
            if offset is None:
                return [Task.model_validate(t) for t in task_data], None
            return [], None

        iterator = PageIterator(fetch_page)

        tasks = await iterator.collect()
        assert len(tasks) == 2

        assert tasks[0].assignee is not None
        assert tasks[0].assignee.name == "Alice"
        assert tasks[0].projects is not None
        assert len(tasks[0].projects) == 1

        assert tasks[1].assignee is not None
        assert tasks[1].assignee.name == "Bob"
        assert tasks[1].projects == []

    async def test_large_result_set_with_namegid(self) -> None:
        """Large result set (5 pages x 100 tasks) with NameGid fields."""
        page_count = [0]

        def make_task(i: int) -> dict[str, Any]:
            return {
                "gid": f"task{i}",
                "name": f"Task {i}",
                "assignee": {"gid": f"user{i % 10}", "name": f"User {i % 10}"},
            }

        async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
            page_count[0] += 1
            if page_count[0] <= 5:
                tasks = [
                    Task.model_validate(make_task(i + (page_count[0] - 1) * 100))
                    for i in range(100)
                ]
                return tasks, f"offset{page_count[0]}"
            return [], None

        iterator = PageIterator(fetch_page)

        # Take first 250 items (should fetch 3 pages)
        tasks = await iterator.take(250)

        assert len(tasks) == 250
        assert page_count[0] == 3

        for task in tasks:
            assert isinstance(task.assignee, NameGid)
