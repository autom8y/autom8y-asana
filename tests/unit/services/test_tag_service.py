"""Unit tests for TagService (WS-B1 / TAG-1 satellite tag read + resolution).

Two-sided coverage of the name-resolution primitive:
- exact-name HIT returns the matching tag(s); MISS returns an empty list.
- case-sensitivity guard: an off-case name does NOT match.
- Asana tag names are not unique -> all exact matches are returned.
- a name scan follows the pagination cursor across pages.
- an unfiltered listing is a single paginated page (limit + offset honored).
- an unconfigured workspace raises ServiceNotConfiguredError (503).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.services.errors import ServiceNotConfiguredError
from autom8_asana.services.tag_service import TagListResult, TagService

WORKSPACE_GID = "1111111111"
PLAY_TAG = {"gid": "1209319457948185", "name": "play_custom_calendar_integration"}
OTHER_TAG = {"gid": "1201265144487000", "name": "Urgent"}


def _make_client(
    *,
    workspace_gid: str | None = WORKSPACE_GID,
    pages: list[tuple[list[dict[str, Any]], str | None]] | None = None,
) -> MagicMock:
    """Build a mock AsanaClient with a scripted get_paginated.

    Args:
        workspace_gid: value for client.default_workspace_gid.
        pages: ordered (data, next_offset) tuples returned by successive
            get_paginated calls. A single-element list yields one page.
    """
    client = MagicMock()
    client.default_workspace_gid = workspace_gid
    if pages is None:
        pages = [([], None)]
    client._http.get_paginated = AsyncMock(side_effect=list(pages))
    return client


@pytest.fixture
def service() -> TagService:
    return TagService()


class TestUnfilteredListing:
    """GET-tags with no name filter: one paginated page."""

    async def test_returns_single_page(self, service: TagService) -> None:
        client = _make_client(pages=[([PLAY_TAG, OTHER_TAG], None)])

        result = await service.list_tags(client)

        assert isinstance(result, TagListResult)
        assert result.data == [PLAY_TAG, OTHER_TAG]
        assert result.has_more is False
        assert result.next_offset is None

    async def test_has_more_when_cursor_present(self, service: TagService) -> None:
        client = _make_client(pages=[([PLAY_TAG], "cursor_abc")])

        result = await service.list_tags(client, limit=1)

        assert result.has_more is True
        assert result.next_offset == "cursor_abc"

    async def test_targets_workspace_tags_endpoint(self, service: TagService) -> None:
        client = _make_client(pages=[([], None)])

        await service.list_tags(client)

        endpoint = client._http.get_paginated.call_args.args[0]
        assert endpoint == f"/workspaces/{WORKSPACE_GID}/tags"

    async def test_passes_offset_cursor(self, service: TagService) -> None:
        client = _make_client(pages=[([], None)])

        await service.list_tags(client, offset="cursor123")

        params = client._http.get_paginated.call_args.kwargs["params"]
        assert params["offset"] == "cursor123"

    async def test_requests_name_in_opt_fields(self, service: TagService) -> None:
        # name is load-bearing for the resolution primitive; it must always be
        # requested so a subsequent name filter can match.
        client = _make_client(pages=[([], None)])

        await service.list_tags(client)

        params = client._http.get_paginated.call_args.kwargs["params"]
        assert "name" in params["opt_fields"]

    async def test_caps_page_size_at_100(self, service: TagService) -> None:
        client = _make_client(pages=[([], None)])

        await service.list_tags(client, limit=100)

        params = client._http.get_paginated.call_args.kwargs["params"]
        assert params["limit"] == 100

    async def test_empty_name_is_unfiltered(self, service: TagService) -> None:
        # `?name=` (empty string) must be treated as "no filter", not as a
        # search for a tag literally named "".
        client = _make_client(pages=[([PLAY_TAG], "cursor_next")])

        result = await service.list_tags(client, name="")

        # Single page fetched (not an all-pages name scan), pagination surfaced.
        assert client._http.get_paginated.call_count == 1
        assert result.data == [PLAY_TAG]
        assert result.next_offset == "cursor_next"


class TestNameResolution:
    """GET-tags?name=X: the exact-match name->GID resolution primitive."""

    async def test_exact_name_hit(self, service: TagService) -> None:
        client = _make_client(pages=[([PLAY_TAG, OTHER_TAG], None)])

        result = await service.list_tags(client, name="play_custom_calendar_integration")

        assert result.data == [PLAY_TAG]
        assert result.has_more is False
        assert result.next_offset is None

    async def test_name_miss_returns_empty_not_error(self, service: TagService) -> None:
        client = _make_client(pages=[([PLAY_TAG, OTHER_TAG], None)])

        result = await service.list_tags(client, name="does_not_exist")

        assert result.data == []
        assert result.has_more is False

    async def test_match_is_case_sensitive(self, service: TagService) -> None:
        # Two-sided guard against the HIT test: an off-case query must MISS.
        client = _make_client(pages=[([PLAY_TAG], None)])

        result = await service.list_tags(client, name="PLAY_CUSTOM_CALENDAR_INTEGRATION")

        assert result.data == []

    async def test_returns_all_duplicate_name_matches(self, service: TagService) -> None:
        # Asana tag names are NOT unique; the primitive surfaces every match.
        dup_a = {"gid": "3001", "name": "Play"}
        dup_b = {"gid": "3002", "name": "Play"}
        client = _make_client(pages=[([dup_a, OTHER_TAG, dup_b], None)])

        result = await service.list_tags(client, name="Play")

        assert result.data == [dup_a, dup_b]

    async def test_scans_across_pages_following_cursor(self, service: TagService) -> None:
        # The match lives on page 2; the scan must follow the cursor to find it.
        page1 = ([OTHER_TAG], "cursor_page2")
        page2 = ([PLAY_TAG], None)
        client = _make_client(pages=[page1, page2])

        result = await service.list_tags(client, name="play_custom_calendar_integration")

        assert result.data == [PLAY_TAG]
        assert client._http.get_paginated.call_count == 2
        # Page 2 was requested with the cursor from page 1.
        second_call_params = client._http.get_paginated.call_args_list[1].kwargs["params"]
        assert second_call_params["offset"] == "cursor_page2"


class TestWorkspaceConfiguration:
    """The service fails closed when no default workspace is configured."""

    async def test_missing_workspace_raises_not_configured(self, service: TagService) -> None:
        client = _make_client(workspace_gid=None)

        with pytest.raises(ServiceNotConfiguredError):
            await service.list_tags(client)

    async def test_missing_workspace_does_not_call_api(self, service: TagService) -> None:
        client = _make_client(workspace_gid=None)

        with pytest.raises(ServiceNotConfiguredError):
            await service.list_tags(client, name="anything")

        client._http.get_paginated.assert_not_called()
