"""Adversarial tests for Phase 2A (Core Models & Pagination) per TDD-0002.

QA/Adversarial validation of:
1. NameGid edge cases
2. PageIterator edge cases
3. Task model with NameGid
4. TasksClient.list_async()

These tests focus on finding problems before production:
- Edge cases and boundary conditions
- Error handling and failure modes
- Concurrent access patterns
- Memory and state management
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from autom8_asana.models import NameGid, PageIterator, Task


# ---------------------------------------------------------------------------
# NameGid Edge Cases
# ---------------------------------------------------------------------------


class TestNameGidValidation:
    """Adversarial tests for NameGid validation edge cases."""

    def test_empty_gid_string(self) -> None:
        """Empty string gid - should this be accepted?

        FINDING: Empty string IS accepted. This may be a gap - empty gid
        is likely never valid from Asana API.
        """
        ref = NameGid(gid="")
        assert ref.gid == ""

    def test_whitespace_only_gid_stripped(self) -> None:
        """Whitespace-only gid becomes empty after strip.

        FINDING: Due to str_strip_whitespace=True, "   " becomes "".
        This could mask bad data.
        """
        ref = NameGid(gid="   ")
        assert ref.gid == ""  # Stripped to empty string

    def test_gid_with_leading_trailing_whitespace(self) -> None:
        """Whitespace around valid gid is stripped."""
        ref = NameGid(gid="  12345  ")
        assert ref.gid == "12345"

    def test_very_long_gid_string(self) -> None:
        """Very long gid string (Asana gids are typically ~16-20 chars)."""
        long_gid = "1" * 1000
        ref = NameGid(gid=long_gid)
        assert ref.gid == long_gid
        assert len(ref.gid) == 1000

    def test_gid_with_special_characters(self) -> None:
        """Gid with special characters - Asana uses numeric gids."""
        # These should technically not be valid Asana gids
        ref = NameGid(gid="abc-123-xyz")
        assert ref.gid == "abc-123-xyz"

    def test_gid_with_unicode(self) -> None:
        """Gid with unicode characters."""
        ref = NameGid(gid="12345")
        assert ref.gid == "12345"

    def test_name_with_unicode(self) -> None:
        """Name field with various unicode characters."""
        test_cases = [
            "Alice",  # emoji
            "cafe resume",  # accented characters
            "",  # CJK characters
            "",  # Arabic
            "",  # Hebrew
            "",  # emojis
        ]
        for name in test_cases:
            ref = NameGid(gid="123", name=name)
            # Whitespace stripping may affect the result
            assert ref.gid == "123"

    def test_name_whitespace_only(self) -> None:
        """Name with only whitespace is stripped to empty string."""
        ref = NameGid(gid="123", name="   ")
        assert ref.name == ""

    def test_name_with_newlines(self) -> None:
        """Name with newlines."""
        ref = NameGid(gid="123", name="Line1\nLine2\nLine3")
        assert "\n" in (ref.name or "")

    def test_name_with_tabs(self) -> None:
        """Name with tabs."""
        ref = NameGid(gid="123", name="Col1\tCol2")
        assert "\t" in (ref.name or "")

    def test_gid_type_coercion_integer_fails(self) -> None:
        """Integer gid should fail validation (Pydantic v2 strict)."""
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

    def test_gid_none_fails(self) -> None:
        """None gid should fail - gid is required."""
        with pytest.raises(ValidationError):
            NameGid(gid=None)  # type: ignore[arg-type]


class TestNameGidSerializationRoundtrip:
    """Tests for NameGid serialization/deserialization roundtrip."""

    def test_model_dump_and_validate_roundtrip(self) -> None:
        """model_dump -> model_validate preserves data."""
        original = NameGid(gid="123", name="Test", resource_type="user")
        dumped = original.model_dump()
        restored = NameGid.model_validate(dumped)

        assert restored == original
        assert restored.gid == original.gid
        assert restored.name == original.name
        assert restored.resource_type == original.resource_type

    def test_json_roundtrip(self) -> None:
        """JSON serialization roundtrip."""
        original = NameGid(gid="456", name="Project")
        json_str = original.model_dump_json()
        parsed = json.loads(json_str)
        restored = NameGid.model_validate(parsed)

        assert restored == original

    def test_model_dump_with_none_values(self) -> None:
        """model_dump includes None values by default."""
        ref = NameGid(gid="123")
        dumped = ref.model_dump()

        assert "name" in dumped
        assert dumped["name"] is None
        assert "resource_type" in dumped
        assert dumped["resource_type"] is None

    def test_model_dump_exclude_none(self) -> None:
        """model_dump(exclude_none=True) excludes None values."""
        ref = NameGid(gid="123")
        dumped = ref.model_dump(exclude_none=True)

        assert "gid" in dumped
        assert "name" not in dumped
        assert "resource_type" not in dumped


class TestNameGidHashingEquality:
    """Edge cases for NameGid hashing and equality."""

    def test_hash_consistency_for_equal_objects(self) -> None:
        """Equal objects must have equal hashes."""
        ref1 = NameGid(gid="123", name="Alice")
        ref2 = NameGid(gid="123", name="Bob")  # Same gid, different name

        assert ref1 == ref2
        assert hash(ref1) == hash(ref2)

    def test_hash_stability(self) -> None:
        """Hash of same object should be stable."""
        ref = NameGid(gid="123", name="Test")
        h1 = hash(ref)
        h2 = hash(ref)
        h3 = hash(ref)

        assert h1 == h2 == h3

    def test_set_membership_with_different_names(self) -> None:
        """Set membership based on gid, not name."""
        s = {NameGid(gid="123", name="Alice")}

        # Same gid, different name - should be "in" the set
        assert NameGid(gid="123", name="Bob") in s
        # Different gid - should not be in the set
        assert NameGid(gid="456", name="Alice") not in s

    def test_dict_key_lookup(self) -> None:
        """Dict key lookup based on gid."""
        d = {NameGid(gid="123", name="Key1"): "value1"}

        # Same gid, different name should find the value
        assert d[NameGid(gid="123", name="Different")] == "value1"

    def test_equality_with_non_namegid_returns_not_implemented(self) -> None:
        """Equality with non-NameGid types returns NotImplemented (not False)."""
        ref = NameGid(gid="123")

        # These comparisons should return False (via NotImplemented)
        assert not (ref == "123")
        assert not (ref == {"gid": "123"})
        assert not (ref == 123)
        assert not (ref == None)

    def test_inequality_operator(self) -> None:
        """!= operator works correctly."""
        ref1 = NameGid(gid="123")
        ref2 = NameGid(gid="456")
        ref3 = NameGid(gid="123")

        assert ref1 != ref2
        assert not (ref1 != ref3)


# ---------------------------------------------------------------------------
# PageIterator Edge Cases
# ---------------------------------------------------------------------------


class TestPageIteratorEmptyResults:
    """Edge cases for empty result sets."""

    async def test_empty_first_page(self) -> None:
        """Empty result on first page."""

        async def fetch_page(offset: str | None) -> tuple[list[str], str | None]:
            return [], None

        iterator = PageIterator(fetch_page)

        # collect should return empty list
        result = await iterator.collect()
        assert result == []

    async def test_first_on_empty_returns_none(self) -> None:
        """first() on empty iterator returns None."""

        async def fetch_page(offset: str | None) -> tuple[list[str], str | None]:
            return [], None

        iterator = PageIterator(fetch_page)
        result = await iterator.first()

        assert result is None

    async def test_take_on_empty_returns_empty(self) -> None:
        """take(n) on empty iterator returns empty list."""

        async def fetch_page(offset: str | None) -> tuple[list[str], str | None]:
            return [], None

        iterator = PageIterator(fetch_page)
        result = await iterator.take(10)

        assert result == []


class TestPageIteratorBoundaryConditions:
    """Boundary condition tests for PageIterator."""

    async def test_single_page_exactly_limit_items(self) -> None:
        """Single page with exactly limit items (no next page)."""
        items = list(range(100))  # Exactly 100 items

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            return items, None  # No next page

        iterator = PageIterator(fetch_page, page_size=100)
        result = await iterator.collect()

        assert result == items

    async def test_take_zero_items(self) -> None:
        """take(0) should return empty list."""

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            return [1, 2, 3], None

        iterator = PageIterator(fetch_page)
        result = await iterator.take(0)

        assert result == []

    async def test_take_negative_items(self) -> None:
        """take(-1) - negative n behavior."""

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            return [1, 2, 3], None

        iterator = PageIterator(fetch_page)
        result = await iterator.take(-1)

        # Should return empty list (count >= -1 is True for first item, so breaks)
        # Actually, -1 >= -1 is True, so loop never executes
        assert result == []


class TestPageIteratorExceptionHandling:
    """Exception handling in PageIterator."""

    async def test_fetch_raises_on_first_page(self) -> None:
        """fetch_page raises exception on first call."""

        async def fetch_page(offset: str | None) -> tuple[list[str], str | None]:
            raise ValueError("Network error")

        iterator = PageIterator(fetch_page)

        with pytest.raises(ValueError, match="Network error"):
            await iterator.collect()

    async def test_fetch_raises_on_second_page(self) -> None:
        """fetch_page raises exception on second page."""
        call_count = [0]

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            call_count[0] += 1
            if call_count[0] == 1:
                return [1, 2], "offset1"
            raise ConnectionError("Connection lost")

        iterator = PageIterator(fetch_page)

        with pytest.raises(ConnectionError, match="Connection lost"):
            await iterator.collect()

        # First page should have been fetched successfully
        assert call_count[0] == 2

    async def test_fetch_raises_during_iteration(self) -> None:
        """Exception during async for iteration."""
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

        # Should have gotten first page items
        assert items == [1, 2, 3]


class TestPageIteratorStateManagement:
    """State management and re-iteration tests."""

    async def test_collect_multiple_times(self) -> None:
        """Calling collect() multiple times on same iterator.

        FINDING: Second collect() returns empty list because iterator
        is exhausted. This is expected behavior but worth documenting.
        """

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            return [1, 2, 3], None

        iterator = PageIterator(fetch_page)

        result1 = await iterator.collect()
        assert result1 == [1, 2, 3]

        # Second call - iterator is exhausted
        result2 = await iterator.collect()
        assert result2 == []  # Empty because exhausted

    async def test_first_then_collect(self) -> None:
        """Calling first() then collect()."""

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            return [1, 2, 3], None

        iterator = PageIterator(fetch_page)

        first = await iterator.first()
        assert first == 1

        # collect() should return remaining items
        remaining = await iterator.collect()
        assert remaining == [2, 3]

    async def test_partial_iteration_then_collect(self) -> None:
        """Partial iteration followed by collect().

        BUG FOUND: take() consumes one extra item from the iterator.
        The async for loop fetches an item BEFORE checking the break condition,
        so item 3 is fetched but never returned when take(2) is called.

        Expected: take(2) returns [1, 2], collect() returns [3, 4, 5]
        Actual: take(2) returns [1, 2], collect() returns [4, 5] (item 3 lost!)

        This is a defect in PageIterator.take() - the break happens after
        __anext__ has already consumed the item from the buffer.
        """

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            return [1, 2, 3, 4, 5], None

        iterator = PageIterator(fetch_page)

        # Take first 2
        items = await iterator.take(2)
        assert items == [1, 2]

        # After take(2), collect() should return remaining items [3, 4, 5]
        rest = await iterator.collect()
        assert rest == [3, 4, 5]

    async def test_iteration_after_exhaustion(self) -> None:
        """Iterating after iterator is exhausted."""

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            return [1], None

        iterator = PageIterator(fetch_page)

        # Exhaust iterator
        await iterator.collect()

        # Further iteration should yield nothing
        items = []
        async for item in iterator:
            items.append(item)

        assert items == []


class TestPageIteratorConcurrency:
    """Concurrent access tests for PageIterator.

    NOTE: PageIterator is NOT designed for concurrent access by multiple
    consumers. These tests document the behavior.
    """

    async def test_concurrent_collect_calls(self) -> None:
        """Two concurrent collect() calls on same iterator.

        FINDING: This leads to race conditions and unpredictable results.
        PageIterator should be used by single consumer.
        """
        call_count = [0]

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            call_count[0] += 1
            await asyncio.sleep(0.01)  # Simulate network delay
            if offset is None:
                return [1, 2], "page2"
            return [3, 4], None

        iterator = PageIterator(fetch_page)

        # Start two concurrent collects
        task1 = asyncio.create_task(iterator.collect())
        task2 = asyncio.create_task(iterator.collect())

        results = await asyncio.gather(task1, task2, return_exceptions=True)

        # The results are unpredictable due to race conditions
        # At minimum, we verify no exceptions were raised
        for result in results:
            assert not isinstance(result, Exception)


class TestPageIteratorMemoryEfficiency:
    """Memory efficiency tests."""

    async def test_large_result_set_streaming(self) -> None:
        """Verify items are yielded without buffering all pages."""
        pages_fetched = []

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            page_num = len(pages_fetched)
            pages_fetched.append(page_num)

            if page_num < 10:  # 10 pages
                return list(
                    range(page_num * 100, (page_num + 1) * 100)
                ), f"page{page_num + 1}"
            return [], None

        iterator = PageIterator(fetch_page)

        # Take only first 50 items
        items = await iterator.take(50)

        assert len(items) == 50
        # Should only have fetched 1 page (first page has 100 items)
        assert len(pages_fetched) == 1

    async def test_buffer_cleared_after_consumption(self) -> None:
        """Buffer is cleared as items are consumed."""

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            return list(range(100)), None

        iterator = PageIterator(fetch_page)

        # Consume all items one by one
        count = 0
        async for _ in iterator:
            count += 1
            # Buffer should be emptying as we consume
            if count == 100:
                assert iterator._buffer == []

        assert count == 100


# ---------------------------------------------------------------------------
# Task Model with NameGid
# ---------------------------------------------------------------------------


class TestTaskNameGidBackwardCompatibility:
    """Backward compatibility: dict input still works for NameGid fields."""

    def test_dict_assignee_converts_to_namegid(self) -> None:
        """Dict for assignee field is converted to NameGid."""
        task = Task.model_validate(
            {
                "gid": "123",
                "assignee": {"gid": "user1", "name": "Alice"},
            }
        )

        assert isinstance(task.assignee, NameGid)
        assert task.assignee.gid == "user1"
        assert task.assignee.name == "Alice"

    def test_dict_projects_converts_to_list_namegid(self) -> None:
        """Dict list for projects field is converted to list[NameGid]."""
        task = Task.model_validate(
            {
                "gid": "123",
                "projects": [
                    {"gid": "proj1", "name": "Project A"},
                    {"gid": "proj2", "name": "Project B"},
                ],
            }
        )

        assert isinstance(task.projects, list)
        assert all(isinstance(p, NameGid) for p in task.projects)
        assert task.projects[0].gid == "proj1"

    def test_mixed_dict_and_namegid_in_list(self) -> None:
        """Mix of dict and NameGid in list field - both should work."""
        # When deserializing from JSON, all would be dicts
        task = Task.model_validate(
            {
                "gid": "123",
                "followers": [
                    {"gid": "f1", "name": "Follower 1"},
                    {"gid": "f2", "name": "Follower 2"},
                ],
            }
        )

        # All should be converted to NameGid
        assert all(isinstance(f, NameGid) for f in (task.followers or []))


class TestTaskNameGidNullHandling:
    """Null vs missing field handling for NameGid fields."""

    def test_null_assignee(self) -> None:
        """Explicit null assignee is accepted."""
        task = Task.model_validate(
            {
                "gid": "123",
                "assignee": None,
            }
        )

        assert task.assignee is None

    def test_missing_assignee(self) -> None:
        """Missing assignee defaults to None."""
        task = Task.model_validate({"gid": "123"})
        assert task.assignee is None

    def test_empty_projects_list(self) -> None:
        """Empty projects list vs None."""
        task_empty = Task.model_validate(
            {
                "gid": "123",
                "projects": [],
            }
        )
        task_none = Task.model_validate(
            {
                "gid": "123",
                "projects": None,
            }
        )
        task_missing = Task.model_validate({"gid": "123"})

        assert task_empty.projects == []
        assert task_none.projects is None
        assert task_missing.projects is None

    def test_null_inside_list_rejected(self) -> None:
        """Null values inside a NameGid list should fail validation."""
        with pytest.raises(ValidationError):
            Task.model_validate(
                {
                    "gid": "123",
                    "projects": [
                        {"gid": "proj1"},
                        None,  # Invalid - can't have None in list[NameGid]
                    ],
                }
            )


class TestTaskModelDumpOutput:
    """model_dump() output format for Task with NameGid."""

    def test_namegid_fields_serialize_to_dict(self) -> None:
        """NameGid fields serialize to dict in model_dump()."""
        task = Task.model_validate(
            {
                "gid": "123",
                "assignee": {"gid": "user1", "name": "Alice"},
                "workspace": {"gid": "ws1", "name": "Workspace"},
            }
        )

        dumped = task.model_dump()

        assert isinstance(dumped["assignee"], dict)
        assert dumped["assignee"]["gid"] == "user1"
        assert dumped["assignee"]["name"] == "Alice"

    def test_list_namegid_fields_serialize_to_list_dict(self) -> None:
        """list[NameGid] fields serialize to list[dict]."""
        task = Task.model_validate(
            {
                "gid": "123",
                "projects": [
                    {"gid": "p1", "name": "Proj1"},
                    {"gid": "p2", "name": "Proj2"},
                ],
            }
        )

        dumped = task.model_dump()

        assert isinstance(dumped["projects"], list)
        assert all(isinstance(p, dict) for p in dumped["projects"])

    def test_json_roundtrip_with_namegid(self) -> None:
        """JSON serialization roundtrip preserves NameGid data."""
        original = Task.model_validate(
            {
                "gid": "123",
                "name": "Test Task",
                "assignee": {"gid": "user1", "name": "Alice"},
                "projects": [{"gid": "p1", "name": "Project"}],
            }
        )

        json_str = original.model_dump_json()
        parsed = json.loads(json_str)
        restored = Task.model_validate(parsed)

        assert restored.assignee == original.assignee
        assert restored.projects == original.projects


class TestTaskNameGidEdgeCases:
    """Edge cases for Task with NameGid fields."""

    def test_assignee_with_extra_fields_ignored(self) -> None:
        """Extra fields in assignee dict are ignored (per ADR-0005)."""
        task = Task.model_validate(
            {
                "gid": "123",
                "assignee": {
                    "gid": "user1",
                    "name": "Alice",
                    "email": "alice@example.com",  # Extra field
                    "photo": {"small": "url"},  # Extra field
                },
            }
        )

        assert task.assignee is not None
        assert task.assignee.gid == "user1"
        assert not hasattr(task.assignee, "email")
        assert not hasattr(task.assignee, "photo")

    def test_namegid_field_with_empty_gid(self) -> None:
        """NameGid field with empty gid string."""
        task = Task.model_validate(
            {
                "gid": "123",
                "assignee": {"gid": "", "name": "Empty GID User"},
            }
        )

        # This is allowed but likely indicates bad data
        assert task.assignee is not None
        assert task.assignee.gid == ""

    def test_completed_by_as_namegid(self) -> None:
        """completed_by field accepts NameGid-compatible dict."""
        task = Task.model_validate(
            {
                "gid": "123",
                "completed": True,
                "completed_by": {"gid": "user1", "name": "Completer"},
            }
        )

        assert isinstance(task.completed_by, NameGid)
        assert task.completed_by.gid == "user1"

    def test_created_by_as_namegid(self) -> None:
        """created_by field accepts NameGid-compatible dict."""
        task = Task.model_validate(
            {
                "gid": "123",
                "created_by": {"gid": "creator1", "name": "Creator"},
            }
        )

        assert isinstance(task.created_by, NameGid)

    def test_parent_as_namegid(self) -> None:
        """parent field (for subtasks) accepts NameGid."""
        task = Task.model_validate(
            {
                "gid": "subtask1",
                "parent": {"gid": "parent1", "name": "Parent Task"},
            }
        )

        assert isinstance(task.parent, NameGid)
        assert task.parent.name == "Parent Task"


# ---------------------------------------------------------------------------
# TasksClient.list_async() Tests
# ---------------------------------------------------------------------------


class TestListAsyncFilterParameters:
    """Tests for TasksClient.list_async() filter parameters."""

    @pytest.fixture
    def mock_http(self) -> AsyncMock:
        """Create mock HTTP client."""
        mock = AsyncMock()
        mock.get_paginated = AsyncMock(return_value=([], None))
        return mock

    @pytest.fixture
    def tasks_client(self, mock_http: AsyncMock) -> Any:
        """Create TasksClient with mocked HTTP."""
        from autom8_asana.clients.tasks import TasksClient
        from autom8_asana.config import AsanaConfig

        class MockAuthProvider:
            def get_secret(self, key: str) -> str:
                return "token"

        return TasksClient(
            http=mock_http,
            config=AsanaConfig(),
            auth_provider=MockAuthProvider(),
        )

    async def test_project_filter(
        self, tasks_client: Any, mock_http: AsyncMock
    ) -> None:
        """Project filter is passed correctly."""
        mock_http.get_paginated.return_value = ([], None)

        iterator = tasks_client.list_async(project="proj123")
        await iterator.collect()

        mock_http.get_paginated.assert_called_once()
        call_args = mock_http.get_paginated.call_args
        params = call_args[1]["params"]
        assert params.get("project") == "proj123"

    async def test_assignee_filter(
        self, tasks_client: Any, mock_http: AsyncMock
    ) -> None:
        """Assignee filter is passed correctly."""
        mock_http.get_paginated.return_value = ([], None)

        iterator = tasks_client.list_async(assignee="me", workspace="ws123")
        await iterator.collect()

        params = mock_http.get_paginated.call_args[1]["params"]
        assert params.get("assignee") == "me"
        assert params.get("workspace") == "ws123"

    async def test_opt_fields_joined(
        self, tasks_client: Any, mock_http: AsyncMock
    ) -> None:
        """opt_fields list is joined with commas."""
        mock_http.get_paginated.return_value = ([], None)

        iterator = tasks_client.list_async(
            project="proj1",
            opt_fields=["name", "completed", "due_on"],
        )
        await iterator.collect()

        params = mock_http.get_paginated.call_args[1]["params"]
        # opt_fields now includes parent.gid automatically and may be reordered
        opt_fields = set(params.get("opt_fields", "").split(","))
        assert {"name", "completed", "due_on"}.issubset(opt_fields)

    async def test_limit_capped_at_100(
        self, tasks_client: Any, mock_http: AsyncMock
    ) -> None:
        """Limit is capped at 100 (Asana max)."""
        mock_http.get_paginated.return_value = ([], None)

        iterator = tasks_client.list_async(project="proj1", limit=200)
        await iterator.collect()

        params = mock_http.get_paginated.call_args[1]["params"]
        assert params.get("limit") == 100  # Capped at 100

    async def test_empty_project_filter_not_included(
        self, tasks_client: Any, mock_http: AsyncMock
    ) -> None:
        """Empty string project filter is not included."""
        mock_http.get_paginated.return_value = ([], None)

        # Empty string is falsy, so should not be included
        iterator = tasks_client.list_async(project="", workspace="ws123")
        await iterator.collect()

        params = mock_http.get_paginated.call_args[1]["params"]
        assert "project" not in params

    async def test_all_filters_combined(
        self, tasks_client: Any, mock_http: AsyncMock
    ) -> None:
        """All filters can be combined."""
        mock_http.get_paginated.return_value = ([], None)

        iterator = tasks_client.list_async(
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

        params = mock_http.get_paginated.call_args[1]["params"]
        assert params["project"] == "proj1"
        assert params["section"] == "sec1"
        assert params["assignee"] == "user1"
        assert params["workspace"] == "ws1"
        assert params["completed_since"] == "2024-01-01T00:00:00Z"
        assert params["modified_since"] == "2024-06-01T00:00:00Z"
        # opt_fields now includes parent.gid automatically
        assert "name" in params["opt_fields"]
        assert params["limit"] == 50


class TestListAsyncPagination:
    """Tests for pagination behavior of list_async()."""

    @pytest.fixture
    def mock_http(self) -> AsyncMock:
        """Create mock HTTP client."""
        mock = AsyncMock()
        mock.get_paginated = AsyncMock()
        return mock

    @pytest.fixture
    def tasks_client(self, mock_http: AsyncMock) -> Any:
        """Create TasksClient with mocked HTTP."""
        from autom8_asana.clients.tasks import TasksClient
        from autom8_asana.config import AsanaConfig

        class MockAuthProvider:
            def get_secret(self, key: str) -> str:
                return "token"

        return TasksClient(
            http=mock_http,
            config=AsanaConfig(),
            auth_provider=MockAuthProvider(),
        )

    async def test_pagination_offset_passed(
        self, tasks_client: Any, mock_http: AsyncMock
    ) -> None:
        """Pagination offset is passed correctly on subsequent pages."""
        # Page 1: returns data and next offset
        # Page 2: returns data and no next offset
        mock_http.get_paginated.side_effect = [
            ([{"gid": "1", "name": "Task 1"}], "offset_abc"),
            ([{"gid": "2", "name": "Task 2"}], None),
        ]

        iterator = tasks_client.list_async(project="proj1")
        tasks = await iterator.collect()

        assert len(tasks) == 2
        assert mock_http.get_paginated.call_count == 2

        # Check second call has offset
        second_call_params = mock_http.get_paginated.call_args_list[1][1]["params"]
        assert second_call_params.get("offset") == "offset_abc"

    async def test_empty_page_stops_iteration(
        self, tasks_client: Any, mock_http: AsyncMock
    ) -> None:
        """Empty page with no offset stops iteration."""
        mock_http.get_paginated.return_value = ([], None)

        iterator = tasks_client.list_async(project="proj1")
        tasks = await iterator.collect()

        assert tasks == []
        assert mock_http.get_paginated.call_count == 1


class TestListAsyncErrorHandling:
    """Error handling tests for list_async()."""

    @pytest.fixture
    def mock_http(self) -> AsyncMock:
        """Create mock HTTP client."""
        mock = AsyncMock()
        mock.get_paginated = AsyncMock()
        return mock

    @pytest.fixture
    def tasks_client(self, mock_http: AsyncMock) -> Any:
        """Create TasksClient with mocked HTTP."""
        from autom8_asana.clients.tasks import TasksClient
        from autom8_asana.config import AsanaConfig

        class MockAuthProvider:
            def get_secret(self, key: str) -> str:
                return "token"

        return TasksClient(
            http=mock_http,
            config=AsanaConfig(),
            auth_provider=MockAuthProvider(),
        )

    async def test_network_error_during_pagination(
        self, tasks_client: Any, mock_http: AsyncMock
    ) -> None:
        """Network error mid-pagination is propagated."""
        from autom8_asana.exceptions import AsanaError

        mock_http.get_paginated.side_effect = [
            ([{"gid": "1"}], "offset1"),
            AsanaError("Network error"),
        ]

        iterator = tasks_client.list_async(project="proj1")

        with pytest.raises(AsanaError, match="Network error"):
            await iterator.collect()

    async def test_invalid_task_data_fails_validation(
        self, tasks_client: Any, mock_http: AsyncMock
    ) -> None:
        """Invalid task data fails Pydantic validation."""
        # Missing required gid field
        mock_http.get_paginated.return_value = (
            [{"name": "No GID Task"}],  # Missing gid
            None,
        )

        iterator = tasks_client.list_async(project="proj1")

        with pytest.raises(ValidationError):
            await iterator.collect()


class TestListAsyncReturnsPageIterator:
    """Tests verifying list_async() returns PageIterator."""

    @pytest.fixture
    def mock_http(self) -> AsyncMock:
        """Create mock HTTP client."""
        mock = AsyncMock()
        mock.get_paginated = AsyncMock(return_value=([], None))
        return mock

    @pytest.fixture
    def tasks_client(self, mock_http: AsyncMock) -> Any:
        """Create TasksClient with mocked HTTP."""
        from autom8_asana.clients.tasks import TasksClient
        from autom8_asana.config import AsanaConfig

        class MockAuthProvider:
            def get_secret(self, key: str) -> str:
                return "token"

        return TasksClient(
            http=mock_http,
            config=AsanaConfig(),
            auth_provider=MockAuthProvider(),
        )

    def test_returns_page_iterator_type(self, tasks_client: Any) -> None:
        """list_async() returns PageIterator instance."""
        result = tasks_client.list_async(project="proj1")

        assert isinstance(result, PageIterator)

    async def test_iterator_methods_available(
        self, tasks_client: Any, mock_http: AsyncMock
    ) -> None:
        """PageIterator methods (collect, first, take) are available."""
        mock_http.get_paginated.return_value = (
            [{"gid": "1"}, {"gid": "2"}, {"gid": "3"}],
            None,
        )

        iterator = tasks_client.list_async(project="proj1")

        # All methods should be available
        assert hasattr(iterator, "collect")
        assert hasattr(iterator, "first")
        assert hasattr(iterator, "take")

        # Can call take
        tasks = await iterator.take(2)
        assert len(tasks) == 2


# ---------------------------------------------------------------------------
# Integration: End-to-End Scenarios
# ---------------------------------------------------------------------------


class TestEndToEndScenarios:
    """End-to-end scenarios combining models and pagination."""

    async def test_iterate_tasks_access_namegid_fields(self) -> None:
        """Iterate tasks and access NameGid fields."""
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

        # Access NameGid fields
        assert tasks[0].assignee is not None
        assert tasks[0].assignee.name == "Alice"
        assert tasks[0].projects is not None
        assert len(tasks[0].projects) == 1

        assert tasks[1].assignee is not None
        assert tasks[1].assignee.name == "Bob"
        assert tasks[1].projects == []

    async def test_large_result_set_with_namegid(self) -> None:
        """Large result set with NameGid fields."""
        page_count = [0]

        def make_task(i: int) -> dict[str, Any]:
            return {
                "gid": f"task{i}",
                "name": f"Task {i}",
                "assignee": {"gid": f"user{i % 10}", "name": f"User {i % 10}"},
            }

        async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
            page_count[0] += 1
            if page_count[0] <= 5:  # 5 pages
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
        assert page_count[0] == 3  # 3 pages fetched

        # Verify NameGid fields work
        for task in tasks:
            assert isinstance(task.assignee, NameGid)
