"""Tests for common models (NameGid, PageIterator).

Per TDD-0002 and ADR-0006: Tests for core models and pagination infrastructure.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autom8_asana.models import NameGid, PageIterator

# ---------------------------------------------------------------------------
# NameGid Tests
# ---------------------------------------------------------------------------


class TestNameGidBasics:
    """Tests for NameGid basic functionality."""

    def test_create_with_gid_only(self) -> None:
        """NameGid can be created with only gid."""
        ref = NameGid(gid="12345")

        assert ref.gid == "12345"
        assert ref.name is None
        assert ref.resource_type is None

    def test_create_with_all_fields(self) -> None:
        """NameGid can be created with all fields."""
        ref = NameGid(gid="12345", name="Alice", resource_type="user")

        assert ref.gid == "12345"
        assert ref.name == "Alice"
        assert ref.resource_type == "user"

    def test_gid_is_required(self) -> None:
        """NameGid requires gid field."""
        with pytest.raises(ValidationError):
            NameGid()  # type: ignore[call-arg]

    def test_model_validate_from_dict(self) -> None:
        """NameGid.model_validate works with dict input."""
        data = {"gid": "123", "name": "Project A", "resource_type": "project"}
        ref = NameGid.model_validate(data)

        assert ref.gid == "123"
        assert ref.name == "Project A"
        assert ref.resource_type == "project"

    def test_extra_fields_ignored(self) -> None:
        """Extra fields in dict are ignored per ADR-0005."""
        data = {
            "gid": "123",
            "name": "User",
            "email": "user@example.com",  # Extra field
            "avatar_url": "https://...",  # Extra field
        }
        ref = NameGid.model_validate(data)

        assert ref.gid == "123"
        assert ref.name == "User"
        assert not hasattr(ref, "email")
        assert not hasattr(ref, "avatar_url")

    def test_whitespace_stripped(self) -> None:
        """String fields have whitespace stripped."""
        ref = NameGid.model_validate(
            {
                "gid": "  123  ",
                "name": "  Test  ",
            }
        )

        assert ref.gid == "123"
        assert ref.name == "Test"


class TestNameGidFrozen:
    """Tests for NameGid immutability (frozen=True)."""

    def test_is_frozen(self) -> None:
        """NameGid is frozen and cannot be modified."""
        ref = NameGid(gid="123", name="Original")

        with pytest.raises(ValidationError):
            ref.name = "Modified"  # type: ignore[misc]

    def test_is_hashable(self) -> None:
        """NameGid is hashable and can be used in sets."""
        ref = NameGid(gid="123", name="Test")

        # Should not raise
        hash(ref)

        # Can be used in a set
        refs = {ref}
        assert ref in refs

    def test_can_be_dict_key(self) -> None:
        """NameGid can be used as dict key."""
        ref1 = NameGid(gid="123", name="Key1")
        ref2 = NameGid(gid="456", name="Key2")

        data = {ref1: "value1", ref2: "value2"}

        assert data[ref1] == "value1"
        assert data[ref2] == "value2"


class TestNameGidEquality:
    """Tests for NameGid equality based on gid only."""

    def test_equality_by_gid(self) -> None:
        """Two NameGids with same gid are equal."""
        ref1 = NameGid(gid="123", name="Alice")
        ref2 = NameGid(gid="123", name="Alice Smith")  # Different name

        assert ref1 == ref2

    def test_inequality_different_gid(self) -> None:
        """NameGids with different gids are not equal."""
        ref1 = NameGid(gid="123", name="Alice")
        ref2 = NameGid(gid="456", name="Alice")  # Same name, different gid

        assert ref1 != ref2

    def test_equality_with_name_vs_none(self) -> None:
        """NameGid with name equals NameGid without name if same gid."""
        ref1 = NameGid(gid="123", name="Alice")
        ref2 = NameGid(gid="123")  # No name

        assert ref1 == ref2

    def test_not_equal_to_other_types(self) -> None:
        """NameGid is not equal to non-NameGid types."""
        ref = NameGid(gid="123", name="Test")

        assert ref != "123"
        assert ref != {"gid": "123"}
        assert ref != 123

    def test_set_deduplication(self) -> None:
        """Set deduplicates NameGids by gid."""
        ref1 = NameGid(gid="123", name="Version 1")
        ref2 = NameGid(gid="123", name="Version 2")
        ref3 = NameGid(gid="456", name="Different")

        refs = {ref1, ref2, ref3}

        # Should have 2 items (123 deduplicated)
        assert len(refs) == 2
        gids = {r.gid for r in refs}
        assert gids == {"123", "456"}


class TestNameGidSerialization:
    """Tests for NameGid serialization."""

    def test_model_dump(self) -> None:
        """model_dump produces dict."""
        ref = NameGid(gid="123", name="Test", resource_type="user")
        dumped = ref.model_dump()

        assert dumped == {"gid": "123", "name": "Test", "resource_type": "user"}

    def test_model_dump_exclude_none(self) -> None:
        """model_dump with exclude_none excludes None values."""
        ref = NameGid(gid="123")
        dumped = ref.model_dump(exclude_none=True)

        assert dumped == {"gid": "123"}
        assert "name" not in dumped
        assert "resource_type" not in dumped


# ---------------------------------------------------------------------------
# PageIterator Tests
# ---------------------------------------------------------------------------


class TestPageIteratorBasics:
    """Tests for PageIterator basic functionality."""

    async def test_empty_result(self) -> None:
        """PageIterator handles empty results."""

        async def fetch_page(offset: str | None) -> tuple[list[str], str | None]:
            return [], None

        iterator = PageIterator(fetch_page)
        result = await iterator.collect()

        assert result == []

    async def test_single_page(self) -> None:
        """PageIterator handles single page."""

        async def fetch_page(offset: str | None) -> tuple[list[str], str | None]:
            return ["a", "b", "c"], None

        iterator = PageIterator(fetch_page)
        result = await iterator.collect()

        assert result == ["a", "b", "c"]

    async def test_multiple_pages(self) -> None:
        """PageIterator handles multiple pages."""
        pages = [
            (["a", "b"], "offset1"),
            (["c", "d"], "offset2"),
            (["e"], None),
        ]
        call_count = [0]

        async def fetch_page(offset: str | None) -> tuple[list[str], str | None]:
            page_data = pages[call_count[0]]
            call_count[0] += 1
            return page_data

        iterator = PageIterator(fetch_page)
        result = await iterator.collect()

        assert result == ["a", "b", "c", "d", "e"]
        assert call_count[0] == 3  # Three pages fetched

    async def test_async_for_iteration(self) -> None:
        """PageIterator works with async for."""

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            return [1, 2, 3], None

        iterator = PageIterator(fetch_page)
        items = []
        async for item in iterator:
            items.append(item)

        assert items == [1, 2, 3]

    async def test_first_returns_first_item(self) -> None:
        """first() returns first item."""

        async def fetch_page(offset: str | None) -> tuple[list[str], str | None]:
            return ["first", "second", "third"], None

        iterator = PageIterator(fetch_page)
        result = await iterator.first()

        assert result == "first"

    async def test_first_returns_none_when_empty(self) -> None:
        """first() returns None for empty results."""

        async def fetch_page(offset: str | None) -> tuple[list[str], str | None]:
            return [], None

        iterator = PageIterator(fetch_page)
        result = await iterator.first()

        assert result is None

    async def test_take_n_items(self) -> None:
        """take(n) returns up to n items."""

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            return [1, 2, 3, 4, 5], None

        iterator = PageIterator(fetch_page)
        result = await iterator.take(3)

        assert result == [1, 2, 3]

    async def test_take_more_than_available(self) -> None:
        """take(n) returns all items if fewer than n available."""

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            return [1, 2], None

        iterator = PageIterator(fetch_page)
        result = await iterator.take(10)

        assert result == [1, 2]


class TestPageIteratorLazyFetching:
    """Tests for PageIterator lazy fetching behavior."""

    async def test_pages_fetched_lazily(self) -> None:
        """Pages are fetched only when needed."""
        call_count = [0]

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            call_count[0] += 1
            if offset is None:
                return [1, 2], "page2"
            return [3, 4], None

        iterator = PageIterator(fetch_page)

        # No fetch until iteration starts
        assert call_count[0] == 0

        # Fetch first item
        item = await iterator.first()
        assert item == 1
        assert call_count[0] == 1  # First page fetched

    async def test_offset_passed_correctly(self) -> None:
        """Offset is passed to fetch_page correctly."""
        offsets: list[str | None] = []

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            offsets.append(offset)
            if offset is None:
                return [1], "offset_A"
            elif offset == "offset_A":
                return [2], "offset_B"
            else:
                return [3], None

        iterator = PageIterator(fetch_page)
        result = await iterator.collect()

        assert result == [1, 2, 3]
        assert offsets == [None, "offset_A", "offset_B"]


class TestPageIteratorMemoryEfficiency:
    """Tests for PageIterator memory efficiency."""

    async def test_buffer_cleared_between_pages(self) -> None:
        """Buffer is cleared as items are yielded."""
        page_num = [0]

        async def fetch_page(offset: str | None) -> tuple[list[int], str | None]:
            page_num[0] += 1
            if page_num[0] == 1:
                return [1, 2, 3], "next"
            else:
                return [4, 5], None

        iterator = PageIterator(fetch_page)

        # Consume first page items
        items = []
        for _ in range(3):
            item = await iterator.__anext__()
            items.append(item)

        # After consuming first page, buffer should be empty
        assert iterator._buffer == []

        # Get next item (should trigger second page fetch)
        item = await iterator.__anext__()
        items.append(item)

        assert items == [1, 2, 3, 4]
