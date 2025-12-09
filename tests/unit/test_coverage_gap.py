"""Tests to fill coverage gaps in low-coverage modules.

This module provides additional test coverage for:
- TeamsClient (clients/teams.py) - 40% -> higher
- StoriesClient (clients/stories.py) - 46% -> higher
- TagsClient (clients/tags.py) - 47% -> higher
- AsyncHTTPClient (transport/http.py) - 47% -> higher

Tests follow established patterns from test_tier2_clients.py and test_http_client.py.
"""

from __future__ import annotations

from typing import Any, AsyncIterator
from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from autom8_asana.clients.stories import StoriesClient
from autom8_asana.clients.tags import TagsClient
from autom8_asana.clients.teams import TeamsClient
from autom8_asana.config import AsanaConfig, RetryConfig
from autom8_asana.exceptions import AsanaError, RateLimitError
from autom8_asana.models import PageIterator, Story, Tag, Team, User
from autom8_asana.models.team import TeamMembership
from autom8_asana.transport.http import AsyncHTTPClient


class MockHTTPClient:
    """Mock HTTP client for testing resource clients."""

    def __init__(self) -> None:
        self.get = AsyncMock()
        self.post = AsyncMock()
        self.put = AsyncMock()
        self.delete = AsyncMock()
        self.get_paginated = AsyncMock()
        self.post_multipart = AsyncMock()
        self.get_stream_url = AsyncMock()


class MockAuthProvider:
    """Mock auth provider."""

    def get_secret(self, key: str) -> str:
        return "test-token"


class MockLogger:
    """Mock logger that records calls."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("debug", msg))

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("info", msg))

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("warning", msg))

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("error", msg))

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("exception", msg))


@pytest.fixture
def mock_http() -> MockHTTPClient:
    """Create mock HTTP client."""
    return MockHTTPClient()


@pytest.fixture
def config() -> AsanaConfig:
    """Default test configuration."""
    return AsanaConfig()


@pytest.fixture
def auth_provider() -> MockAuthProvider:
    """Mock auth provider."""
    return MockAuthProvider()


@pytest.fixture
def logger() -> MockLogger:
    """Mock logger."""
    return MockLogger()


# =============================================================================
# TeamsClient Full Coverage Tests
# =============================================================================


@pytest.fixture
def teams_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> TeamsClient:
    """Create TeamsClient with mocked dependencies."""
    return TeamsClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


class TestTeamsClientGetAsyncRaw:
    """Tests for TeamsClient.get_async() with raw=True."""

    async def test_get_async_raw_returns_dict(
        self, teams_client: TeamsClient, mock_http: MockHTTPClient
    ) -> None:
        """get_async with raw=True returns dict."""
        mock_http.get.return_value = {
            "gid": "team123",
            "name": "Engineering",
        }

        result = await teams_client.get_async("team123", raw=True)

        assert isinstance(result, dict)
        assert result["gid"] == "team123"


class TestTeamsClientGetAsyncOptFields:
    """Tests for TeamsClient.get_async() with opt_fields."""

    async def test_get_async_with_opt_fields(
        self, teams_client: TeamsClient, mock_http: MockHTTPClient
    ) -> None:
        """get_async passes opt_fields to params."""
        mock_http.get.return_value = {
            "gid": "team123",
            "name": "Engineering",
            "description": "Eng team",
        }

        result = await teams_client.get_async(
            "team123", opt_fields=["name", "description"]
        )

        assert isinstance(result, Team)
        mock_http.get.assert_called_once_with(
            "/teams/team123", params={"opt_fields": "name,description"}
        )


class TestTeamsClientGetSync:
    """Tests for TeamsClient.get() sync method."""

    def test_get_sync_returns_team_model(
        self, teams_client: TeamsClient, mock_http: MockHTTPClient
    ) -> None:
        """get() sync method returns Team model by default."""
        mock_http.get.return_value = {
            "gid": "team123",
            "name": "Engineering",
        }

        result = teams_client.get("team123")

        assert isinstance(result, Team)
        assert result.gid == "team123"

    def test_get_sync_raw_returns_dict(
        self, teams_client: TeamsClient, mock_http: MockHTTPClient
    ) -> None:
        """get() sync with raw=True returns dict."""
        mock_http.get.return_value = {"gid": "team123", "name": "Engineering"}

        result = teams_client.get("team123", raw=True)

        assert isinstance(result, dict)
        assert result["gid"] == "team123"


class TestTeamsClientAddUserAsyncRaw:
    """Tests for TeamsClient.add_user_async() with raw=True."""

    async def test_add_user_async_raw_returns_dict(
        self, teams_client: TeamsClient, mock_http: MockHTTPClient
    ) -> None:
        """add_user_async with raw=True returns dict."""
        mock_http.post.return_value = {
            "gid": "mem123",
            "user": {"gid": "user1"},
            "team": {"gid": "team123"},
        }

        result = await teams_client.add_user_async("team123", user="user1", raw=True)

        assert isinstance(result, dict)
        assert result["gid"] == "mem123"


class TestTeamsClientAddUserSync:
    """Tests for TeamsClient.add_user() sync method."""

    def test_add_user_sync_returns_membership(
        self, teams_client: TeamsClient, mock_http: MockHTTPClient
    ) -> None:
        """add_user() sync method returns TeamMembership model."""
        mock_http.post.return_value = {
            "gid": "mem123",
            "user": {"gid": "user1"},
            "team": {"gid": "team123"},
            "is_guest": False,
        }

        result = teams_client.add_user("team123", user="user1")

        assert isinstance(result, TeamMembership)
        assert result.gid == "mem123"

    def test_add_user_sync_raw_returns_dict(
        self, teams_client: TeamsClient, mock_http: MockHTTPClient
    ) -> None:
        """add_user() sync with raw=True returns dict."""
        mock_http.post.return_value = {
            "gid": "mem123",
            "user": {"gid": "user1"},
        }

        result = teams_client.add_user("team123", user="user1", raw=True)

        assert isinstance(result, dict)
        assert result["gid"] == "mem123"


class TestTeamsClientRemoveUserAsync:
    """Tests for TeamsClient.remove_user_async()."""

    async def test_remove_user_async_calls_post(
        self, teams_client: TeamsClient, mock_http: MockHTTPClient
    ) -> None:
        """remove_user_async makes POST request to removeUser endpoint."""
        mock_http.post.return_value = {}

        await teams_client.remove_user_async("team123", user="user1")

        mock_http.post.assert_called_once_with(
            "/teams/team123/removeUser", json={"data": {"user": "user1"}}
        )


class TestTeamsClientRemoveUserSync:
    """Tests for TeamsClient.remove_user() sync method."""

    def test_remove_user_sync_calls_post(
        self, teams_client: TeamsClient, mock_http: MockHTTPClient
    ) -> None:
        """remove_user() sync method makes POST request."""
        mock_http.post.return_value = {}

        teams_client.remove_user("team123", user="user1")

        mock_http.post.assert_called_once_with(
            "/teams/team123/removeUser", json={"data": {"user": "user1"}}
        )


class TestTeamsClientListForUserAsync:
    """Tests for TeamsClient.list_for_user_async()."""

    async def test_list_for_user_async_returns_page_iterator(
        self, teams_client: TeamsClient, mock_http: MockHTTPClient
    ) -> None:
        """list_for_user_async returns PageIterator[Team]."""
        mock_http.get_paginated.return_value = (
            [
                {"gid": "team1", "name": "Team 1"},
                {"gid": "team2", "name": "Team 2"},
            ],
            None,
        )

        iterator = teams_client.list_for_user_async("user123")

        assert isinstance(iterator, PageIterator)
        items = await iterator.collect()
        assert len(items) == 2
        assert all(isinstance(t, Team) for t in items)

    async def test_list_for_user_async_with_organization(
        self, teams_client: TeamsClient, mock_http: MockHTTPClient
    ) -> None:
        """list_for_user_async passes organization filter."""
        mock_http.get_paginated.return_value = (
            [{"gid": "team1", "name": "Team 1"}],
            None,
        )

        iterator = teams_client.list_for_user_async("user123", organization="org456")

        await iterator.collect()
        call_args = mock_http.get_paginated.call_args
        assert call_args[1]["params"]["organization"] == "org456"

    async def test_list_for_user_async_with_pagination(
        self, teams_client: TeamsClient, mock_http: MockHTTPClient
    ) -> None:
        """list_for_user_async handles pagination."""
        mock_http.get_paginated.side_effect = [
            ([{"gid": "team1", "name": "Team 1"}], "offset123"),
            ([{"gid": "team2", "name": "Team 2"}], None),
        ]

        iterator = teams_client.list_for_user_async("user123", limit=1)
        items = await iterator.collect()

        assert len(items) == 2
        assert mock_http.get_paginated.call_count == 2


class TestTeamsClientListForWorkspaceAsync:
    """Tests for TeamsClient.list_for_workspace_async()."""

    async def test_list_for_workspace_async_returns_page_iterator(
        self, teams_client: TeamsClient, mock_http: MockHTTPClient
    ) -> None:
        """list_for_workspace_async returns PageIterator[Team]."""
        mock_http.get_paginated.return_value = (
            [
                {"gid": "team1", "name": "Team 1"},
                {"gid": "team2", "name": "Team 2"},
            ],
            None,
        )

        iterator = teams_client.list_for_workspace_async("ws123")

        assert isinstance(iterator, PageIterator)
        items = await iterator.collect()
        assert len(items) == 2
        assert all(isinstance(t, Team) for t in items)

    async def test_list_for_workspace_async_with_opt_fields(
        self, teams_client: TeamsClient, mock_http: MockHTTPClient
    ) -> None:
        """list_for_workspace_async passes opt_fields."""
        mock_http.get_paginated.return_value = ([], None)

        iterator = teams_client.list_for_workspace_async(
            "ws123", opt_fields=["name", "description"]
        )
        await iterator.collect()

        call_args = mock_http.get_paginated.call_args
        assert call_args[1]["params"]["opt_fields"] == "name,description"


class TestTeamsClientListUsersAsync:
    """Tests for TeamsClient.list_users_async()."""

    async def test_list_users_async_returns_page_iterator_of_users(
        self, teams_client: TeamsClient, mock_http: MockHTTPClient
    ) -> None:
        """list_users_async returns PageIterator[User]."""
        mock_http.get_paginated.return_value = (
            [
                {"gid": "user1", "name": "Alice"},
                {"gid": "user2", "name": "Bob"},
            ],
            None,
        )

        iterator = teams_client.list_users_async("team123")

        assert isinstance(iterator, PageIterator)
        items = await iterator.collect()
        assert len(items) == 2
        assert all(isinstance(u, User) for u in items)

    async def test_list_users_async_with_pagination(
        self, teams_client: TeamsClient, mock_http: MockHTTPClient
    ) -> None:
        """list_users_async handles pagination correctly."""
        mock_http.get_paginated.side_effect = [
            ([{"gid": "user1", "name": "Alice"}], "next_offset"),
            ([{"gid": "user2", "name": "Bob"}], None),
        ]

        iterator = teams_client.list_users_async("team123", limit=1)
        items = await iterator.collect()

        assert len(items) == 2


# =============================================================================
# StoriesClient Full Coverage Tests
# =============================================================================


@pytest.fixture
def stories_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> StoriesClient:
    """Create StoriesClient with mocked dependencies."""
    return StoriesClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


class TestStoriesClientGetAsyncRaw:
    """Tests for StoriesClient.get_async() with raw=True."""

    async def test_get_async_raw_returns_dict(
        self, stories_client: StoriesClient, mock_http: MockHTTPClient
    ) -> None:
        """get_async with raw=True returns dict."""
        mock_http.get.return_value = {
            "gid": "story123",
            "text": "Test comment",
        }

        result = await stories_client.get_async("story123", raw=True)

        assert isinstance(result, dict)
        assert result["gid"] == "story123"


class TestStoriesClientGetSync:
    """Tests for StoriesClient.get() sync method."""

    def test_get_sync_returns_story_model(
        self, stories_client: StoriesClient, mock_http: MockHTTPClient
    ) -> None:
        """get() sync method returns Story model by default."""
        mock_http.get.return_value = {
            "gid": "story123",
            "resource_subtype": "comment_added",
            "text": "Test comment",
        }

        result = stories_client.get("story123")

        assert isinstance(result, Story)
        assert result.gid == "story123"

    def test_get_sync_raw_returns_dict(
        self, stories_client: StoriesClient, mock_http: MockHTTPClient
    ) -> None:
        """get() sync with raw=True returns dict."""
        mock_http.get.return_value = {"gid": "story123", "text": "Comment"}

        result = stories_client.get("story123", raw=True)

        assert isinstance(result, dict)
        assert result["gid"] == "story123"


class TestStoriesClientUpdateAsync:
    """Tests for StoriesClient.update_async()."""

    async def test_update_async_returns_story_model(
        self, stories_client: StoriesClient, mock_http: MockHTTPClient
    ) -> None:
        """update_async returns Story model by default."""
        mock_http.put.return_value = {
            "gid": "story123",
            "text": "Updated comment",
            "is_pinned": True,
        }

        result = await stories_client.update_async(
            "story123", text="Updated comment", is_pinned=True
        )

        assert isinstance(result, Story)
        assert result.text == "Updated comment"

    async def test_update_async_raw_returns_dict(
        self, stories_client: StoriesClient, mock_http: MockHTTPClient
    ) -> None:
        """update_async with raw=True returns dict."""
        mock_http.put.return_value = {"gid": "story123", "text": "Updated"}

        result = await stories_client.update_async("story123", text="Updated", raw=True)

        assert isinstance(result, dict)
        assert result["text"] == "Updated"

    async def test_update_async_with_html_text(
        self, stories_client: StoriesClient, mock_http: MockHTTPClient
    ) -> None:
        """update_async passes html_text correctly."""
        mock_http.put.return_value = {
            "gid": "story123",
            "html_text": "<body><strong>Bold</strong></body>",
        }

        await stories_client.update_async(
            "story123", html_text="<body><strong>Bold</strong></body>"
        )

        call_args = mock_http.put.call_args
        assert (
            call_args[1]["json"]["data"]["html_text"]
            == "<body><strong>Bold</strong></body>"
        )


class TestStoriesClientUpdateSync:
    """Tests for StoriesClient.update() sync method."""

    def test_update_sync_returns_story_model(
        self, stories_client: StoriesClient, mock_http: MockHTTPClient
    ) -> None:
        """update() sync method returns Story model by default."""
        mock_http.put.return_value = {"gid": "story123", "text": "Updated"}

        result = stories_client.update("story123", text="Updated")

        assert isinstance(result, Story)

    def test_update_sync_raw_returns_dict(
        self, stories_client: StoriesClient, mock_http: MockHTTPClient
    ) -> None:
        """update() sync with raw=True returns dict."""
        mock_http.put.return_value = {"gid": "story123", "text": "Updated"}

        result = stories_client.update("story123", text="Updated", raw=True)

        assert isinstance(result, dict)


class TestStoriesClientDeleteAsync:
    """Tests for StoriesClient.delete_async()."""

    async def test_delete_async_calls_delete(
        self, stories_client: StoriesClient, mock_http: MockHTTPClient
    ) -> None:
        """delete_async makes DELETE request."""
        mock_http.delete.return_value = {}

        await stories_client.delete_async("story123")

        mock_http.delete.assert_called_once_with("/stories/story123")


class TestStoriesClientDeleteSync:
    """Tests for StoriesClient.delete() sync method."""

    def test_delete_sync_calls_delete(
        self, stories_client: StoriesClient, mock_http: MockHTTPClient
    ) -> None:
        """delete() sync method makes DELETE request."""
        mock_http.delete.return_value = {}

        stories_client.delete("story123")

        mock_http.delete.assert_called_once_with("/stories/story123")


class TestStoriesClientListForTaskAsync:
    """Tests for StoriesClient.list_for_task_async()."""

    async def test_list_for_task_async_returns_page_iterator(
        self, stories_client: StoriesClient, mock_http: MockHTTPClient
    ) -> None:
        """list_for_task_async returns PageIterator[Story]."""
        mock_http.get_paginated.return_value = (
            [
                {"gid": "story1", "text": "Comment 1"},
                {"gid": "story2", "text": "Comment 2"},
            ],
            None,
        )

        iterator = stories_client.list_for_task_async("task123")

        assert isinstance(iterator, PageIterator)
        items = await iterator.collect()
        assert len(items) == 2
        assert all(isinstance(s, Story) for s in items)

    async def test_list_for_task_async_with_pagination(
        self, stories_client: StoriesClient, mock_http: MockHTTPClient
    ) -> None:
        """list_for_task_async handles pagination."""
        mock_http.get_paginated.side_effect = [
            ([{"gid": "story1", "text": "Comment 1"}], "offset_abc"),
            ([{"gid": "story2", "text": "Comment 2"}], None),
        ]

        iterator = stories_client.list_for_task_async("task123", limit=1)
        items = await iterator.collect()

        assert len(items) == 2
        assert mock_http.get_paginated.call_count == 2


class TestStoriesClientCreateCommentAsyncRaw:
    """Tests for StoriesClient.create_comment_async() with raw=True."""

    async def test_create_comment_async_raw_returns_dict(
        self, stories_client: StoriesClient, mock_http: MockHTTPClient
    ) -> None:
        """create_comment_async with raw=True returns dict."""
        mock_http.post.return_value = {"gid": "story123", "text": "New comment"}

        result = await stories_client.create_comment_async(
            task="task1", text="New comment", raw=True
        )

        assert isinstance(result, dict)
        assert result["text"] == "New comment"

    async def test_create_comment_async_with_html_text_and_pinned(
        self, stories_client: StoriesClient, mock_http: MockHTTPClient
    ) -> None:
        """create_comment_async passes html_text and is_pinned."""
        mock_http.post.return_value = {
            "gid": "story123",
            "text": "New comment",
            "is_pinned": True,
        }

        await stories_client.create_comment_async(
            task="task1",
            text="New comment",
            html_text="<body>New comment</body>",
            is_pinned=True,
        )

        call_args = mock_http.post.call_args
        data = call_args[1]["json"]["data"]
        assert data["text"] == "New comment"
        assert data["html_text"] == "<body>New comment</body>"
        assert data["is_pinned"] is True


class TestStoriesClientCreateCommentSync:
    """Tests for StoriesClient.create_comment() sync method."""

    def test_create_comment_sync_returns_story_model(
        self, stories_client: StoriesClient, mock_http: MockHTTPClient
    ) -> None:
        """create_comment() sync method returns Story model by default."""
        mock_http.post.return_value = {
            "gid": "story123",
            "resource_subtype": "comment_added",
            "text": "New comment",
        }

        result = stories_client.create_comment(task="task1", text="New comment")

        assert isinstance(result, Story)
        assert result.text == "New comment"

    def test_create_comment_sync_raw_returns_dict(
        self, stories_client: StoriesClient, mock_http: MockHTTPClient
    ) -> None:
        """create_comment() sync with raw=True returns dict."""
        mock_http.post.return_value = {"gid": "story123", "text": "New comment"}

        result = stories_client.create_comment(
            task="task1", text="New comment", raw=True
        )

        assert isinstance(result, dict)


# =============================================================================
# TagsClient Full Coverage Tests
# =============================================================================


@pytest.fixture
def tags_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> TagsClient:
    """Create TagsClient with mocked dependencies."""
    return TagsClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


class TestTagsClientGetAsyncRaw:
    """Tests for TagsClient.get_async() with raw=True."""

    async def test_get_async_raw_returns_dict(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """get_async with raw=True returns dict."""
        mock_http.get.return_value = {"gid": "tag123", "name": "Priority"}

        result = await tags_client.get_async("tag123", raw=True)

        assert isinstance(result, dict)
        assert result["gid"] == "tag123"


class TestTagsClientGetSync:
    """Tests for TagsClient.get() sync method."""

    def test_get_sync_returns_tag_model(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """get() sync method returns Tag model by default."""
        mock_http.get.return_value = {"gid": "tag123", "name": "Priority"}

        result = tags_client.get("tag123")

        assert isinstance(result, Tag)
        assert result.gid == "tag123"

    def test_get_sync_raw_returns_dict(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """get() sync with raw=True returns dict."""
        mock_http.get.return_value = {"gid": "tag123", "name": "Priority"}

        result = tags_client.get("tag123", raw=True)

        assert isinstance(result, dict)


class TestTagsClientCreateAsyncRaw:
    """Tests for TagsClient.create_async() with raw=True."""

    async def test_create_async_raw_returns_dict(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async with raw=True returns dict."""
        mock_http.post.return_value = {"gid": "tag123", "name": "Priority"}

        result = await tags_client.create_async(
            workspace="ws1", name="Priority", raw=True
        )

        assert isinstance(result, dict)
        assert result["name"] == "Priority"

    async def test_create_async_with_notes(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async passes notes parameter."""
        mock_http.post.return_value = {
            "gid": "tag123",
            "name": "Priority",
            "notes": "High priority tasks",
        }

        await tags_client.create_async(
            workspace="ws1", name="Priority", notes="High priority tasks"
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["data"]["notes"] == "High priority tasks"


class TestTagsClientCreateSync:
    """Tests for TagsClient.create() sync method."""

    def test_create_sync_returns_tag_model(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """create() sync method returns Tag model by default."""
        mock_http.post.return_value = {"gid": "tag123", "name": "Priority"}

        result = tags_client.create(workspace="ws1", name="Priority")

        assert isinstance(result, Tag)

    def test_create_sync_raw_returns_dict(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """create() sync with raw=True returns dict."""
        mock_http.post.return_value = {"gid": "tag123", "name": "Priority"}

        result = tags_client.create(workspace="ws1", name="Priority", raw=True)

        assert isinstance(result, dict)


class TestTagsClientUpdateAsync:
    """Tests for TagsClient.update_async()."""

    async def test_update_async_returns_tag_model(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """update_async returns Tag model by default."""
        mock_http.put.return_value = {"gid": "tag123", "name": "Updated Tag"}

        result = await tags_client.update_async("tag123", name="Updated Tag")

        assert isinstance(result, Tag)
        assert result.name == "Updated Tag"

    async def test_update_async_raw_returns_dict(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """update_async with raw=True returns dict."""
        mock_http.put.return_value = {"gid": "tag123", "name": "Updated Tag"}

        result = await tags_client.update_async("tag123", raw=True, name="Updated Tag")

        assert isinstance(result, dict)


class TestTagsClientUpdateSync:
    """Tests for TagsClient.update() sync method."""

    def test_update_sync_returns_tag_model(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """update() sync method returns Tag model by default."""
        mock_http.put.return_value = {"gid": "tag123", "name": "Updated"}

        result = tags_client.update("tag123", name="Updated")

        assert isinstance(result, Tag)

    def test_update_sync_raw_returns_dict(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """update() sync with raw=True returns dict."""
        mock_http.put.return_value = {"gid": "tag123", "name": "Updated"}

        result = tags_client.update("tag123", raw=True, name="Updated")

        assert isinstance(result, dict)


class TestTagsClientDeleteAsync:
    """Tests for TagsClient.delete_async()."""

    async def test_delete_async_calls_delete(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """delete_async makes DELETE request."""
        mock_http.delete.return_value = {}

        await tags_client.delete_async("tag123")

        mock_http.delete.assert_called_once_with("/tags/tag123")


class TestTagsClientDeleteSync:
    """Tests for TagsClient.delete() sync method."""

    def test_delete_sync_calls_delete(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """delete() sync method makes DELETE request."""
        mock_http.delete.return_value = {}

        tags_client.delete("tag123")

        mock_http.delete.assert_called_once_with("/tags/tag123")


class TestTagsClientListForWorkspaceAsync:
    """Tests for TagsClient.list_for_workspace_async()."""

    async def test_list_for_workspace_async_returns_page_iterator(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """list_for_workspace_async returns PageIterator[Tag]."""
        mock_http.get_paginated.return_value = (
            [
                {"gid": "tag1", "name": "Priority"},
                {"gid": "tag2", "name": "Bug"},
            ],
            None,
        )

        iterator = tags_client.list_for_workspace_async("ws123")

        assert isinstance(iterator, PageIterator)
        items = await iterator.collect()
        assert len(items) == 2
        assert all(isinstance(t, Tag) for t in items)

    async def test_list_for_workspace_async_with_pagination(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """list_for_workspace_async handles pagination."""
        mock_http.get_paginated.side_effect = [
            ([{"gid": "tag1", "name": "Priority"}], "next_offset"),
            ([{"gid": "tag2", "name": "Bug"}], None),
        ]

        iterator = tags_client.list_for_workspace_async("ws123", limit=1)
        items = await iterator.collect()

        assert len(items) == 2


class TestTagsClientListForTaskAsync:
    """Tests for TagsClient.list_for_task_async()."""

    async def test_list_for_task_async_returns_page_iterator(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """list_for_task_async returns PageIterator[Tag]."""
        mock_http.get_paginated.return_value = (
            [{"gid": "tag1", "name": "Priority"}],
            None,
        )

        iterator = tags_client.list_for_task_async("task123")

        assert isinstance(iterator, PageIterator)
        items = await iterator.collect()
        assert len(items) == 1
        assert isinstance(items[0], Tag)


class TestTagsClientAddToTaskAsync:
    """Tests for TagsClient.add_to_task_async()."""

    async def test_add_to_task_async_calls_post(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """add_to_task_async makes POST request to addTag endpoint."""
        mock_http.post.return_value = {}

        await tags_client.add_to_task_async("task123", tag="tag456")

        mock_http.post.assert_called_once_with(
            "/tasks/task123/addTag", json={"data": {"tag": "tag456"}}
        )


class TestTagsClientAddToTaskSync:
    """Tests for TagsClient.add_to_task() sync method."""

    def test_add_to_task_sync_calls_post(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """add_to_task() sync method makes POST request."""
        mock_http.post.return_value = {}

        tags_client.add_to_task("task123", tag="tag456")

        mock_http.post.assert_called_once_with(
            "/tasks/task123/addTag", json={"data": {"tag": "tag456"}}
        )


class TestTagsClientRemoveFromTaskAsync:
    """Tests for TagsClient.remove_from_task_async()."""

    async def test_remove_from_task_async_calls_post(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """remove_from_task_async makes POST request to removeTag endpoint."""
        mock_http.post.return_value = {}

        await tags_client.remove_from_task_async("task123", tag="tag456")

        mock_http.post.assert_called_once_with(
            "/tasks/task123/removeTag", json={"data": {"tag": "tag456"}}
        )


class TestTagsClientRemoveFromTaskSync:
    """Tests for TagsClient.remove_from_task() sync method."""

    def test_remove_from_task_sync_calls_post(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """remove_from_task() sync method makes POST request."""
        mock_http.post.return_value = {}

        tags_client.remove_from_task("task123", tag="tag456")

        mock_http.post.assert_called_once_with(
            "/tasks/task123/removeTag", json={"data": {"tag": "tag456"}}
        )


# =============================================================================
# AsyncHTTPClient Full Coverage Tests
# =============================================================================


@pytest.fixture
def http_config() -> AsanaConfig:
    """HTTP client test configuration."""
    return AsanaConfig(
        base_url="https://app.asana.com/api/1.0",
        retry=RetryConfig(
            max_retries=2,
            base_delay=0.01,
            jitter=False,
        ),
    )


@pytest.fixture
def http_client(
    http_config: AsanaConfig, auth_provider: MockAuthProvider
) -> AsyncHTTPClient:
    """Create AsyncHTTPClient for testing."""
    return AsyncHTTPClient(http_config, auth_provider)


class TestAsyncHTTPClientGetPaginated:
    """Tests for AsyncHTTPClient.get_paginated()."""

    @respx.mock
    async def test_get_paginated_returns_data_and_offset(
        self, http_client: AsyncHTTPClient
    ) -> None:
        """get_paginated returns data list and next offset."""
        respx.get("https://app.asana.com/api/1.0/tasks").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [{"gid": "1"}, {"gid": "2"}],
                    "next_page": {"offset": "next123"},
                },
            )
        )

        data, offset = await http_client.get_paginated("/tasks")

        assert data == [{"gid": "1"}, {"gid": "2"}]
        assert offset == "next123"
        await http_client.close()

    @respx.mock
    async def test_get_paginated_no_next_page(
        self, http_client: AsyncHTTPClient
    ) -> None:
        """get_paginated returns None offset when no more pages."""
        respx.get("https://app.asana.com/api/1.0/tasks").mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"gid": "1"}]},
            )
        )

        data, offset = await http_client.get_paginated("/tasks")

        assert data == [{"gid": "1"}]
        assert offset is None
        await http_client.close()

    @respx.mock
    async def test_get_paginated_handles_rate_limit(
        self, http_config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """get_paginated retries on 429 rate limit."""
        retry_config = AsanaConfig(
            base_url=http_config.base_url,
            retry=RetryConfig(max_retries=2, base_delay=0.01, jitter=False),
        )
        client = AsyncHTTPClient(retry_config, auth_provider)

        route = respx.get("https://app.asana.com/api/1.0/tasks")
        route.side_effect = [
            httpx.Response(
                429,
                json={"errors": [{"message": "Rate limit"}]},
                headers={"Retry-After": "1"},
            ),
            httpx.Response(200, json={"data": [{"gid": "1"}]}),
        ]

        data, offset = await client.get_paginated("/tasks")

        assert data == [{"gid": "1"}]
        assert route.call_count == 2
        await client.close()

    @respx.mock
    async def test_get_paginated_handles_timeout(
        self, http_config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """get_paginated retries on timeout."""
        retry_config = AsanaConfig(
            base_url=http_config.base_url,
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.01,
                jitter=False,
                retryable_status_codes=frozenset({429, 503, 504}),
            ),
        )
        client = AsyncHTTPClient(retry_config, auth_provider)

        route = respx.get("https://app.asana.com/api/1.0/tasks")
        route.side_effect = [
            httpx.TimeoutException("Timeout"),
            httpx.Response(200, json={"data": [{"gid": "1"}]}),
        ]

        data, offset = await client.get_paginated("/tasks")

        assert data == [{"gid": "1"}]
        assert route.call_count == 2
        await client.close()

    @respx.mock
    async def test_get_paginated_invalid_json_raises_error(
        self, http_client: AsyncHTTPClient
    ) -> None:
        """get_paginated raises AsanaError on invalid JSON."""
        respx.get("https://app.asana.com/api/1.0/tasks").mock(
            return_value=httpx.Response(
                200,
                content=b"Not JSON",
                headers={"X-Request-Id": "req-xyz"},
            )
        )

        with pytest.raises(AsanaError) as exc_info:
            await http_client.get_paginated("/tasks")

        assert "Invalid JSON response" in str(exc_info.value)
        await http_client.close()


class TestAsyncHTTPClientPostMultipart:
    """Tests for AsyncHTTPClient.post_multipart()."""

    @respx.mock
    async def test_post_multipart_uploads_file(
        self, http_client: AsyncHTTPClient
    ) -> None:
        """post_multipart sends multipart form data."""
        respx.post("https://app.asana.com/api/1.0/tasks/123/attachments").mock(
            return_value=httpx.Response(
                200,
                json={"data": {"gid": "att123", "name": "test.txt"}},
            )
        )

        result = await http_client.post_multipart(
            "/tasks/123/attachments",
            files={"file": ("test.txt", b"Hello world", "text/plain")},
            data={"parent": "123"},
        )

        assert result == {"gid": "att123", "name": "test.txt"}
        await http_client.close()

    @respx.mock
    async def test_post_multipart_handles_rate_limit(
        self, http_config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """post_multipart retries on rate limit."""
        retry_config = AsanaConfig(
            base_url=http_config.base_url,
            retry=RetryConfig(max_retries=2, base_delay=0.01, jitter=False),
        )
        client = AsyncHTTPClient(retry_config, auth_provider)

        route = respx.post("https://app.asana.com/api/1.0/tasks/123/attachments")
        route.side_effect = [
            httpx.Response(
                429,
                json={"errors": [{"message": "Rate limit"}]},
                headers={"Retry-After": "1"},
            ),
            httpx.Response(200, json={"data": {"gid": "att123"}}),
        ]

        result = await client.post_multipart(
            "/tasks/123/attachments",
            files={"file": ("test.txt", b"Hello", "text/plain")},
        )

        assert result == {"gid": "att123"}
        assert route.call_count == 2
        await client.close()

    @respx.mock
    async def test_post_multipart_handles_server_error_retry(
        self, http_config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """post_multipart retries on retryable server error."""
        retry_config = AsanaConfig(
            base_url=http_config.base_url,
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.01,
                jitter=False,
                retryable_status_codes=frozenset({429, 503, 504}),
            ),
        )
        client = AsyncHTTPClient(retry_config, auth_provider)

        route = respx.post("https://app.asana.com/api/1.0/tasks/123/attachments")
        route.side_effect = [
            httpx.Response(503, json={"errors": [{"message": "Unavailable"}]}),
            httpx.Response(200, json={"data": {"gid": "att123"}}),
        ]

        result = await client.post_multipart(
            "/tasks/123/attachments",
            files={"file": ("test.txt", b"Hello", "text/plain")},
        )

        assert result == {"gid": "att123"}
        await client.close()

    @respx.mock
    async def test_post_multipart_handles_timeout(
        self, http_config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """post_multipart retries on timeout."""
        retry_config = AsanaConfig(
            base_url=http_config.base_url,
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.01,
                jitter=False,
                retryable_status_codes=frozenset({429, 503, 504}),
            ),
        )
        client = AsyncHTTPClient(retry_config, auth_provider)

        route = respx.post("https://app.asana.com/api/1.0/tasks/123/attachments")
        route.side_effect = [
            httpx.TimeoutException("Timeout"),
            httpx.Response(200, json={"data": {"gid": "att123"}}),
        ]

        result = await client.post_multipart(
            "/tasks/123/attachments",
            files={"file": ("test.txt", b"Hello", "text/plain")},
        )

        assert result == {"gid": "att123"}
        await client.close()

    @respx.mock
    async def test_post_multipart_invalid_json_raises_error(
        self, http_client: AsyncHTTPClient
    ) -> None:
        """post_multipart raises AsanaError on invalid JSON response."""
        respx.post("https://app.asana.com/api/1.0/tasks/123/attachments").mock(
            return_value=httpx.Response(
                200,
                content=b"Not JSON",
                headers={"X-Request-Id": "req-abc"},
            )
        )

        with pytest.raises(AsanaError) as exc_info:
            await http_client.post_multipart(
                "/tasks/123/attachments",
                files={"file": ("test.txt", b"Hello", "text/plain")},
            )

        assert "Invalid JSON response" in str(exc_info.value)
        await http_client.close()


class TestAsyncHTTPClientStream:
    """Tests for AsyncHTTPClient.stream() context manager."""

    @respx.mock
    async def test_stream_yields_response(self, http_client: AsyncHTTPClient) -> None:
        """stream() context manager yields httpx Response."""
        respx.get("https://app.asana.com/api/1.0/attachments/123/download").mock(
            return_value=httpx.Response(
                200,
                content=b"file content here",
            )
        )

        async with http_client.stream(
            "GET", "/attachments/123/download"
        ) as response:
            assert isinstance(response, httpx.Response)
            content = await response.aread()
            assert content == b"file content here"

        await http_client.close()


class TestAsyncHTTPClientGetStreamUrl:
    """Tests for AsyncHTTPClient.get_stream_url()."""

    @respx.mock
    async def test_get_stream_url_yields_chunks(
        self, http_client: AsyncHTTPClient
    ) -> None:
        """get_stream_url yields byte chunks from URL."""
        respx.get("https://example.com/download/file.pdf").mock(
            return_value=httpx.Response(
                200,
                content=b"chunk1chunk2chunk3",
            )
        )

        chunks: list[bytes] = []
        async for chunk in http_client.get_stream_url(
            "https://example.com/download/file.pdf"
        ):
            chunks.append(chunk)

        assert b"".join(chunks) == b"chunk1chunk2chunk3"
        await http_client.close()

    @respx.mock
    async def test_get_stream_url_raises_on_error(
        self, http_client: AsyncHTTPClient
    ) -> None:
        """get_stream_url raises AsanaError on HTTP error."""
        respx.get("https://example.com/download/file.pdf").mock(
            return_value=httpx.Response(404)
        )

        with pytest.raises(AsanaError) as exc_info:
            async for _ in http_client.get_stream_url(
                "https://example.com/download/file.pdf"
            ):
                pass

        assert "Failed to download" in str(exc_info.value)
        await http_client.close()


class TestAsyncHTTPClientWithLogger:
    """Tests for AsyncHTTPClient with logger enabled."""

    @respx.mock
    async def test_request_logs_debug_message(
        self,
        http_config: AsanaConfig,
        auth_provider: MockAuthProvider,
        logger: MockLogger,
    ) -> None:
        """Request with logger logs debug message."""
        client = AsyncHTTPClient(http_config, auth_provider, logger)

        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(200, json={"data": {"gid": "123"}})
        )

        await client.get("/tasks/123")

        assert any("GET /tasks/123" in msg for _, msg in logger.messages)
        await client.close()

    @respx.mock
    async def test_post_multipart_logs_debug_message(
        self,
        http_config: AsanaConfig,
        auth_provider: MockAuthProvider,
        logger: MockLogger,
    ) -> None:
        """post_multipart with logger logs debug message."""
        client = AsyncHTTPClient(http_config, auth_provider, logger)

        respx.post("https://app.asana.com/api/1.0/tasks/123/attachments").mock(
            return_value=httpx.Response(200, json={"data": {"gid": "att123"}})
        )

        await client.post_multipart(
            "/tasks/123/attachments",
            files={"file": ("test.txt", b"Hello", "text/plain")},
        )

        assert any("multipart" in msg for _, msg in logger.messages)
        await client.close()

    @respx.mock
    async def test_get_paginated_logs_debug_message(
        self,
        http_config: AsanaConfig,
        auth_provider: MockAuthProvider,
        logger: MockLogger,
    ) -> None:
        """get_paginated with logger logs debug message."""
        client = AsyncHTTPClient(http_config, auth_provider, logger)

        respx.get("https://app.asana.com/api/1.0/tasks").mock(
            return_value=httpx.Response(200, json={"data": [{"gid": "1"}]})
        )

        await client.get_paginated("/tasks")

        assert any("paginated" in msg for _, msg in logger.messages)
        await client.close()


class TestAsyncHTTPClientHTTPError:
    """Tests for AsyncHTTPClient handling of httpx.HTTPError."""

    @respx.mock
    async def test_request_http_error_raises_asana_error(
        self, http_client: AsyncHTTPClient
    ) -> None:
        """HTTP error other than timeout raises AsanaError."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(AsanaError) as exc_info:
            await http_client.get("/tasks/123")

        assert "HTTP error" in str(exc_info.value)
        await http_client.close()

    @respx.mock
    async def test_get_paginated_http_error_raises_asana_error(
        self, http_client: AsyncHTTPClient
    ) -> None:
        """HTTP error in get_paginated raises AsanaError."""
        respx.get("https://app.asana.com/api/1.0/tasks").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(AsanaError) as exc_info:
            await http_client.get_paginated("/tasks")

        assert "HTTP error" in str(exc_info.value)
        await http_client.close()

    @respx.mock
    async def test_post_multipart_http_error_raises_asana_error(
        self, http_client: AsyncHTTPClient
    ) -> None:
        """HTTP error in post_multipart raises AsanaError."""
        respx.post("https://app.asana.com/api/1.0/tasks/123/attachments").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(AsanaError) as exc_info:
            await http_client.post_multipart(
                "/tasks/123/attachments",
                files={"file": ("test.txt", b"Hello", "text/plain")},
            )

        assert "HTTP error" in str(exc_info.value)
        await http_client.close()


class TestAsyncHTTPClientTimeoutExhausted:
    """Tests for AsyncHTTPClient when timeout exhausts retries."""

    @respx.mock
    async def test_get_paginated_timeout_exhausted_raises_timeout_error(
        self, http_config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """get_paginated raises TimeoutError when retries exhausted."""
        from autom8_asana.exceptions import TimeoutError

        retry_config = AsanaConfig(
            base_url=http_config.base_url,
            retry=RetryConfig(
                max_retries=1,
                base_delay=0.01,
                jitter=False,
                retryable_status_codes=frozenset({429, 503, 504}),
            ),
        )
        client = AsyncHTTPClient(retry_config, auth_provider)

        route = respx.get("https://app.asana.com/api/1.0/tasks")
        route.side_effect = [
            httpx.TimeoutException("Timeout 1"),
            httpx.TimeoutException("Timeout 2"),
        ]

        with pytest.raises(TimeoutError):
            await client.get_paginated("/tasks")

        await client.close()

    @respx.mock
    async def test_post_multipart_timeout_exhausted_raises_timeout_error(
        self, http_config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """post_multipart raises TimeoutError when retries exhausted."""
        from autom8_asana.exceptions import TimeoutError

        retry_config = AsanaConfig(
            base_url=http_config.base_url,
            retry=RetryConfig(
                max_retries=1,
                base_delay=0.01,
                jitter=False,
                retryable_status_codes=frozenset({429, 503, 504}),
            ),
        )
        client = AsyncHTTPClient(retry_config, auth_provider)

        route = respx.post("https://app.asana.com/api/1.0/tasks/123/attachments")
        route.side_effect = [
            httpx.TimeoutException("Timeout 1"),
            httpx.TimeoutException("Timeout 2"),
        ]

        with pytest.raises(TimeoutError):
            await client.post_multipart(
                "/tasks/123/attachments",
                files={"file": ("test.txt", b"Hello", "text/plain")},
            )

        await client.close()


class TestAsyncHTTPClientResponseWithoutDataWrapper:
    """Tests for responses without data wrapper."""

    @respx.mock
    async def test_post_multipart_returns_unwrapped_data(
        self, http_client: AsyncHTTPClient
    ) -> None:
        """post_multipart unwraps data field from response."""
        respx.post("https://app.asana.com/api/1.0/tasks/123/attachments").mock(
            return_value=httpx.Response(
                200,
                json={"data": {"gid": "att123", "name": "file.txt"}},
            )
        )

        result = await http_client.post_multipart(
            "/tasks/123/attachments",
            files={"file": ("test.txt", b"Hello", "text/plain")},
        )

        assert result == {"gid": "att123", "name": "file.txt"}
        await http_client.close()

    @respx.mock
    async def test_post_multipart_returns_response_without_data_wrapper(
        self, http_client: AsyncHTTPClient
    ) -> None:
        """post_multipart returns response as-is when no data wrapper."""
        respx.post("https://app.asana.com/api/1.0/tasks/123/attachments").mock(
            return_value=httpx.Response(
                200,
                json={"result": "success", "id": "123"},
            )
        )

        result = await http_client.post_multipart(
            "/tasks/123/attachments",
            files={"file": ("test.txt", b"Hello", "text/plain")},
        )

        assert result == {"result": "success", "id": "123"}
        await http_client.close()
