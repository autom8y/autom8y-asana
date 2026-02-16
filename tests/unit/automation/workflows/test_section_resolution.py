"""Tests for section_resolution module.

Per TDD-SECTION-ENUM-001 Section 7.1: Unit tests for resolve_section_gids()
covering happy path, partial match, no match, case insensitivity, empty
sections list, exception propagation, and OFFER_CLASSIFIER contract test.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from autom8_asana.automation.workflows.section_resolution import (
    resolve_section_gids,
)
from autom8_asana.models.section import Section

# --- Helpers ---


class _AsyncIterator:
    """Async iterator for mock page iterators."""

    def __init__(self, items: list[Any]) -> None:
        self._items = items
        self._index = 0

    def __aiter__(self) -> _AsyncIterator:
        return self

    async def __anext__(self) -> Any:
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item

    async def collect(self) -> list[Any]:
        return self._items


def _make_section(gid: str, name: str) -> Section:
    """Create a Section model instance for testing."""
    return Section(gid=gid, name=name)


# --- Tests ---


@pytest.mark.asyncio
async def test_resolve_all_names_found():
    """All target names match sections in the project."""
    sections = [
        _make_section("sec-1", "Converted"),
        _make_section("sec-2", "Did Not Convert"),
        _make_section("sec-3", "In Progress"),
    ]
    mock_client = MagicMock()
    mock_client.list_for_project_async.return_value = _AsyncIterator(sections)

    result = await resolve_section_gids(
        mock_client,
        "proj-123",
        {"Converted", "Did Not Convert"},
    )

    assert result == {"converted": "sec-1", "did not convert": "sec-2"}
    mock_client.list_for_project_async.assert_called_once_with("proj-123")


@pytest.mark.asyncio
async def test_resolve_partial_match(caplog):
    """Some target names match, others produce WARNING log."""
    sections = [
        _make_section("sec-1", "Converted"),
        _make_section("sec-2", "In Progress"),
    ]
    mock_client = MagicMock()
    mock_client.list_for_project_async.return_value = _AsyncIterator(sections)

    result = await resolve_section_gids(
        mock_client,
        "proj-123",
        {"Converted", "NONEXISTENT"},
    )

    # Only the matched section is returned
    assert result == {"converted": "sec-1"}
    assert "nonexistent" not in result


@pytest.mark.asyncio
async def test_resolve_no_match():
    """No target names match, returns empty dict."""
    sections = [
        _make_section("sec-1", "In Progress"),
        _make_section("sec-2", "Complete"),
    ]
    mock_client = MagicMock()
    mock_client.list_for_project_async.return_value = _AsyncIterator(sections)

    result = await resolve_section_gids(
        mock_client,
        "proj-123",
        {"Converted", "Did Not Convert"},
    )

    assert result == {}


@pytest.mark.asyncio
async def test_resolve_case_insensitive():
    """'CONVERTED' matches section named 'Converted' (case-insensitive)."""
    sections = [
        _make_section("sec-1", "Converted"),
        _make_section("sec-2", "DID NOT CONVERT"),
    ]
    mock_client = MagicMock()
    mock_client.list_for_project_async.return_value = _AsyncIterator(sections)

    result = await resolve_section_gids(
        mock_client,
        "proj-123",
        {"CONVERTED", "did not convert"},
    )

    assert "converted" in result
    assert result["converted"] == "sec-1"
    assert "did not convert" in result
    assert result["did not convert"] == "sec-2"


@pytest.mark.asyncio
async def test_resolve_empty_sections_list():
    """Project has no sections, returns empty dict."""
    mock_client = MagicMock()
    mock_client.list_for_project_async.return_value = _AsyncIterator([])

    result = await resolve_section_gids(
        mock_client,
        "proj-123",
        {"Converted"},
    )

    assert result == {}


@pytest.mark.asyncio
async def test_resolve_propagates_exception():
    """SectionsClient raises, exception propagates to caller."""

    class _FailingIterator:
        async def collect(self):
            raise ConnectionError("API timeout")

    mock_client = MagicMock()
    mock_client.list_for_project_async.return_value = _FailingIterator()

    with pytest.raises(ConnectionError, match="API timeout"):
        await resolve_section_gids(
            mock_client,
            "proj-123",
            {"Converted"},
        )


def test_offer_active_section_count():
    """OFFER_CLASSIFIER has exactly 21 ACTIVE sections.

    Contract test per TDD-SECTION-ENUM-001 Section 7.4: guards against
    accidental classifier changes that would silently alter enumeration
    behavior.
    """
    from autom8_asana.models.business.activity import (
        OFFER_CLASSIFIER,
        AccountActivity,
    )

    active = OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVE)
    assert len(active) == 21


@pytest.mark.asyncio
async def test_resolve_with_frozenset_target():
    """Accepts frozenset as target_names (type union contract)."""
    sections = [
        _make_section("sec-1", "Active"),
        _make_section("sec-2", "Inactive"),
    ]
    mock_client = MagicMock()
    mock_client.list_for_project_async.return_value = _AsyncIterator(sections)

    result = await resolve_section_gids(
        mock_client,
        "proj-123",
        frozenset({"Active", "Inactive"}),
    )

    assert result == {"active": "sec-1", "inactive": "sec-2"}


@pytest.mark.asyncio
async def test_resolve_section_with_none_name_skipped():
    """Sections with name=None are excluded from the lookup."""
    sections = [
        _make_section("sec-1", "Converted"),
        Section(gid="sec-no-name"),  # name defaults to None
    ]
    mock_client = MagicMock()
    mock_client.list_for_project_async.return_value = _AsyncIterator(sections)

    result = await resolve_section_gids(
        mock_client,
        "proj-123",
        {"Converted"},
    )

    assert result == {"converted": "sec-1"}
