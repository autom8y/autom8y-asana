"""Tests for Tier 2 Resource Clients (TDD-0004).

Tests WebhooksClient, TeamsClient, AttachmentsClient, TagsClient,
GoalsClient, PortfoliosClient, and StoriesClient.
Follows Tier 1 test patterns with mocked HTTP dependencies.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any
from unittest.mock import AsyncMock

import pytest

from autom8_asana.clients.attachments import AttachmentsClient
from autom8_asana.clients.goals import GoalsClient
from autom8_asana.clients.portfolios import PortfoliosClient
from autom8_asana.clients.stories import StoriesClient
from autom8_asana.clients.tags import TagsClient
from autom8_asana.clients.teams import TeamsClient
from autom8_asana.clients.webhooks import WebhooksClient
from autom8_asana.config import AsanaConfig
from autom8_asana.models import (
    Attachment,
    Goal,
    Portfolio,
    Story,
    Tag,
    Team,
    Webhook,
)
from autom8_asana.models.team import TeamMembership


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
# WebhooksClient Tests
# =============================================================================


@pytest.fixture
def webhooks_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> WebhooksClient:
    """Create WebhooksClient with mocked dependencies."""
    return WebhooksClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


class TestWebhooksClientGetAsync:
    """Tests for WebhooksClient.get_async()."""

    async def test_get_async_returns_webhook_model(
        self, webhooks_client: WebhooksClient, mock_http: MockHTTPClient
    ) -> None:
        """get_async returns Webhook model by default."""
        mock_http.get.return_value = {
            "gid": "wh123",
            "target": "https://example.com/webhook",
            "active": True,
        }

        result = await webhooks_client.get_async("wh123")

        assert isinstance(result, Webhook)
        assert result.gid == "wh123"
        assert result.target == "https://example.com/webhook"
        assert result.active is True
        mock_http.get.assert_called_once_with("/webhooks/wh123", params={})

    async def test_get_async_raw_returns_dict(
        self, webhooks_client: WebhooksClient, mock_http: MockHTTPClient
    ) -> None:
        """get_async with raw=True returns dict."""
        mock_http.get.return_value = {"gid": "wh123", "target": "https://example.com"}

        result = await webhooks_client.get_async("wh123", raw=True)

        assert isinstance(result, dict)
        assert result["gid"] == "wh123"


class TestWebhooksClientCreateAsync:
    """Tests for WebhooksClient.create_async()."""

    async def test_create_async_returns_webhook_model(
        self, webhooks_client: WebhooksClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async returns Webhook model by default."""
        mock_http.post.return_value = {
            "gid": "wh123",
            "target": "https://example.com/webhook",
            "active": True,
            "resource": {"gid": "proj123"},
        }

        result = await webhooks_client.create_async(
            resource="proj123", target="https://example.com/webhook"
        )

        assert isinstance(result, Webhook)
        assert result.gid == "wh123"
        mock_http.post.assert_called_once_with(
            "/webhooks",
            json={
                "data": {"resource": "proj123", "target": "https://example.com/webhook"}
            },
        )


class TestWebhooksSignatureVerification:
    """Tests for WebhooksClient signature verification (per ADR-0008)."""

    def test_verify_signature_valid(self) -> None:
        """verify_signature returns True for valid signature."""
        # Known test vector
        secret = "test_secret"
        body = b'{"events": []}'
        # Pre-computed HMAC-SHA256 of body with secret
        import hashlib
        import hmac

        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        result = WebhooksClient.verify_signature(body, expected, secret)
        assert result is True

    def test_verify_signature_invalid(self) -> None:
        """verify_signature returns False for invalid signature."""
        result = WebhooksClient.verify_signature(
            b'{"events": []}', "invalid_signature", "test_secret"
        )
        assert result is False

    def test_extract_handshake_secret_present(self) -> None:
        """extract_handshake_secret returns secret when present."""
        headers = {"X-Hook-Secret": "my_secret_123", "Content-Type": "application/json"}
        result = WebhooksClient.extract_handshake_secret(headers)
        assert result == "my_secret_123"

    def test_extract_handshake_secret_case_insensitive(self) -> None:
        """extract_handshake_secret is case-insensitive."""
        headers = {"x-hook-secret": "my_secret_123"}
        result = WebhooksClient.extract_handshake_secret(headers)
        assert result == "my_secret_123"

    def test_extract_handshake_secret_missing(self) -> None:
        """extract_handshake_secret returns None when not present."""
        headers = {"Content-Type": "application/json"}
        result = WebhooksClient.extract_handshake_secret(headers)
        assert result is None


# =============================================================================
# TeamsClient Tests
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


class TestTeamsClientGetAsync:
    """Tests for TeamsClient.get_async()."""

    async def test_get_async_returns_team_model(
        self, teams_client: TeamsClient, mock_http: MockHTTPClient
    ) -> None:
        """get_async returns Team model by default."""
        mock_http.get.return_value = {
            "gid": "team123",
            "name": "Engineering",
            "organization": {"gid": "org1", "name": "Acme Corp"},
        }

        result = await teams_client.get_async("team123")

        assert isinstance(result, Team)
        assert result.gid == "team123"
        assert result.name == "Engineering"
        mock_http.get.assert_called_once_with("/teams/team123", params={})


class TestTeamsClientAddUserAsync:
    """Tests for TeamsClient.add_user_async()."""

    async def test_add_user_async_returns_membership(
        self, teams_client: TeamsClient, mock_http: MockHTTPClient
    ) -> None:
        """add_user_async returns TeamMembership model."""
        mock_http.post.return_value = {
            "gid": "mem123",
            "user": {"gid": "user1", "name": "Alice"},
            "team": {"gid": "team123", "name": "Engineering"},
            "is_guest": False,
        }

        result = await teams_client.add_user_async("team123", user="user1")

        assert isinstance(result, TeamMembership)
        assert result.gid == "mem123"
        mock_http.post.assert_called_once_with(
            "/teams/team123/addUser", json={"data": {"user": "user1"}}
        )


# =============================================================================
# TagsClient Tests
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


class TestTagsClientGetAsync:
    """Tests for TagsClient.get_async()."""

    async def test_get_async_returns_tag_model(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """get_async returns Tag model by default."""
        mock_http.get.return_value = {
            "gid": "tag123",
            "name": "Priority",
            "color": "dark-red",
        }

        result = await tags_client.get_async("tag123")

        assert isinstance(result, Tag)
        assert result.gid == "tag123"
        assert result.name == "Priority"
        assert result.color == "dark-red"
        mock_http.get.assert_called_once_with("/tags/tag123", params={})


class TestTagsClientCreateAsync:
    """Tests for TagsClient.create_async()."""

    async def test_create_async_returns_tag_model(
        self, tags_client: TagsClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async returns Tag model by default."""
        mock_http.post.return_value = {
            "gid": "tag123",
            "name": "Priority",
            "color": "dark-blue",
        }

        result = await tags_client.create_async(
            workspace="ws1", name="Priority", color="dark-blue"
        )

        assert isinstance(result, Tag)
        assert result.gid == "tag123"
        mock_http.post.assert_called_once_with(
            "/tags",
            json={
                "data": {"workspace": "ws1", "name": "Priority", "color": "dark-blue"}
            },
        )


# =============================================================================
# StoriesClient Tests
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


class TestStoriesClientGetAsync:
    """Tests for StoriesClient.get_async()."""

    async def test_get_async_returns_story_model(
        self, stories_client: StoriesClient, mock_http: MockHTTPClient
    ) -> None:
        """get_async returns Story model by default."""
        mock_http.get.return_value = {
            "gid": "story123",
            "resource_subtype": "comment_added",
            "text": "This is a comment",
            "created_by": {"gid": "user1", "name": "Alice"},
        }

        result = await stories_client.get_async("story123")

        assert isinstance(result, Story)
        assert result.gid == "story123"
        assert result.resource_subtype == "comment_added"
        assert result.text == "This is a comment"
        mock_http.get.assert_called_once_with("/stories/story123", params={})


class TestStoriesClientCreateCommentAsync:
    """Tests for StoriesClient.create_comment_async()."""

    async def test_create_comment_async_returns_story_model(
        self, stories_client: StoriesClient, mock_http: MockHTTPClient
    ) -> None:
        """create_comment_async returns Story model by default."""
        mock_http.post.return_value = {
            "gid": "story123",
            "resource_subtype": "comment_added",
            "text": "Great work!",
        }

        result = await stories_client.create_comment_async(
            task="task1", text="Great work!"
        )

        assert isinstance(result, Story)
        assert result.text == "Great work!"
        mock_http.post.assert_called_once_with(
            "/tasks/task1/stories", json={"data": {"text": "Great work!"}}
        )


# =============================================================================
# AttachmentsClient Tests
# =============================================================================


@pytest.fixture
def attachments_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> AttachmentsClient:
    """Create AttachmentsClient with mocked dependencies."""
    return AttachmentsClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


class TestAttachmentsClientGetAsync:
    """Tests for AttachmentsClient.get_async()."""

    async def test_get_async_returns_attachment_model(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """get_async returns Attachment model by default."""
        mock_http.get.return_value = {
            "gid": "att123",
            "name": "report.pdf",
            "size": 1024,
            "host": "asana",
        }

        result = await attachments_client.get_async("att123")

        assert isinstance(result, Attachment)
        assert result.gid == "att123"
        assert result.name == "report.pdf"
        assert result.size == 1024
        mock_http.get.assert_called_once_with("/attachments/att123", params={})


class TestAttachmentsClientUploadAsync:
    """Tests for AttachmentsClient.upload_async()."""

    async def test_upload_async_returns_attachment_model(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """upload_async returns Attachment model by default."""
        mock_http.post_multipart.return_value = {
            "gid": "att123",
            "name": "test.txt",
            "size": 11,
        }

        file_obj = BytesIO(b"hello world")
        result = await attachments_client.upload_async(
            parent="task1", file=file_obj, name="test.txt"
        )

        assert isinstance(result, Attachment)
        assert result.gid == "att123"
        assert result.name == "test.txt"
        mock_http.post_multipart.assert_called_once()
        call_args = mock_http.post_multipart.call_args
        assert call_args[0][0] == "/tasks/task1/attachments"


class TestAttachmentsClientExternalAsync:
    """Tests for AttachmentsClient.create_external_async()."""

    async def test_create_external_async_returns_attachment(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """create_external_async returns Attachment model."""
        mock_http.post.return_value = {
            "gid": "att456",
            "name": "External Link",
            "host": "external",
            "view_url": "https://example.com/doc",
        }

        result = await attachments_client.create_external_async(
            parent="task1", url="https://example.com/doc", name="External Link"
        )

        assert isinstance(result, Attachment)
        assert result.host == "external"
        mock_http.post.assert_called_once_with(
            "/tasks/task1/attachments",
            json={
                "data": {
                    "resource_subtype": "external",
                    "url": "https://example.com/doc",
                    "name": "External Link",
                }
            },
        )


# =============================================================================
# GoalsClient Tests
# =============================================================================


@pytest.fixture
def goals_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> GoalsClient:
    """Create GoalsClient with mocked dependencies."""
    return GoalsClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


class TestGoalsClientGetAsync:
    """Tests for GoalsClient.get_async()."""

    async def test_get_async_returns_goal_model(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """get_async returns Goal model by default."""
        mock_http.get.return_value = {
            "gid": "goal123",
            "name": "Q4 Revenue Target",
            "status": "on_track",
        }

        result = await goals_client.get_async("goal123")

        assert isinstance(result, Goal)
        assert result.gid == "goal123"
        assert result.name == "Q4 Revenue Target"
        assert result.status == "on_track"
        mock_http.get.assert_called_once_with("/goals/goal123", params={})


class TestGoalsClientCreateAsync:
    """Tests for GoalsClient.create_async()."""

    async def test_create_async_returns_goal_model(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async returns Goal model by default."""
        mock_http.post.return_value = {
            "gid": "goal123",
            "name": "Increase Revenue",
            "workspace": {"gid": "ws1"},
        }

        result = await goals_client.create_async(
            workspace="ws1", name="Increase Revenue", due_on="2024-12-31"
        )

        assert isinstance(result, Goal)
        assert result.gid == "goal123"
        mock_http.post.assert_called_once()
        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["workspace"] == "ws1"
        assert call_data["name"] == "Increase Revenue"
        assert call_data["due_on"] == "2024-12-31"


class TestGoalsClientSubgoals:
    """Tests for GoalsClient subgoal operations."""

    async def test_add_subgoal_async_returns_goal(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """add_subgoal_async returns updated parent goal."""
        mock_http.post.return_value = {
            "gid": "goal123",
            "name": "Parent Goal",
        }

        result = await goals_client.add_subgoal_async("goal123", subgoal="subgoal456")

        assert isinstance(result, Goal)
        mock_http.post.assert_called_once_with(
            "/goals/goal123/addSubgoal", json={"data": {"subgoal": "subgoal456"}}
        )


# =============================================================================
# PortfoliosClient Tests
# =============================================================================


@pytest.fixture
def portfolios_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> PortfoliosClient:
    """Create PortfoliosClient with mocked dependencies."""
    return PortfoliosClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


class TestPortfoliosClientGetAsync:
    """Tests for PortfoliosClient.get_async()."""

    async def test_get_async_returns_portfolio_model(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """get_async returns Portfolio model by default."""
        mock_http.get.return_value = {
            "gid": "port123",
            "name": "Q4 Projects",
            "owner": {"gid": "user1", "name": "Alice"},
        }

        result = await portfolios_client.get_async("port123")

        assert isinstance(result, Portfolio)
        assert result.gid == "port123"
        assert result.name == "Q4 Projects"
        mock_http.get.assert_called_once_with("/portfolios/port123", params={})


class TestPortfoliosClientCreateAsync:
    """Tests for PortfoliosClient.create_async()."""

    async def test_create_async_returns_portfolio_model(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async returns Portfolio model by default."""
        mock_http.post.return_value = {
            "gid": "port123",
            "name": "New Portfolio",
            "color": "dark-green",
        }

        result = await portfolios_client.create_async(
            workspace="ws1", name="New Portfolio", color="dark-green"
        )

        assert isinstance(result, Portfolio)
        assert result.gid == "port123"
        mock_http.post.assert_called_once_with(
            "/portfolios",
            json={
                "data": {
                    "workspace": "ws1",
                    "name": "New Portfolio",
                    "color": "dark-green",
                }
            },
        )


class TestPortfoliosClientItems:
    """Tests for PortfoliosClient item operations."""

    async def test_add_item_async(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """add_item_async adds project to portfolio."""
        mock_http.post.return_value = {}

        await portfolios_client.add_item_async("port123", item="proj456")

        mock_http.post.assert_called_once_with(
            "/portfolios/port123/addItem", json={"data": {"item": "proj456"}}
        )


# =============================================================================
# AsanaClient Integration Tests
# =============================================================================


class TestAsanaClientTier2Properties:
    """Tests for Tier 2 client properties on AsanaClient."""

    def test_webhooks_property_returns_webhooks_client(self) -> None:
        """webhooks property returns WebhooksClient instance."""
        from autom8_asana import AsanaClient

        client = AsanaClient(token="test-token")
        assert isinstance(client.webhooks, WebhooksClient)

    def test_teams_property_returns_teams_client(self) -> None:
        """teams property returns TeamsClient instance."""
        from autom8_asana import AsanaClient

        client = AsanaClient(token="test-token")
        assert isinstance(client.teams, TeamsClient)

    def test_attachments_property_returns_attachments_client(self) -> None:
        """attachments property returns AttachmentsClient instance."""
        from autom8_asana import AsanaClient

        client = AsanaClient(token="test-token")
        assert isinstance(client.attachments, AttachmentsClient)

    def test_tags_property_returns_tags_client(self) -> None:
        """tags property returns TagsClient instance."""
        from autom8_asana import AsanaClient

        client = AsanaClient(token="test-token")
        assert isinstance(client.tags, TagsClient)

    def test_goals_property_returns_goals_client(self) -> None:
        """goals property returns GoalsClient instance."""
        from autom8_asana import AsanaClient

        client = AsanaClient(token="test-token")
        assert isinstance(client.goals, GoalsClient)

    def test_portfolios_property_returns_portfolios_client(self) -> None:
        """portfolios property returns PortfoliosClient instance."""
        from autom8_asana import AsanaClient

        client = AsanaClient(token="test-token")
        assert isinstance(client.portfolios, PortfoliosClient)

    def test_stories_property_returns_stories_client(self) -> None:
        """stories property returns StoriesClient instance."""
        from autom8_asana import AsanaClient

        client = AsanaClient(token="test-token")
        assert isinstance(client.stories, StoriesClient)


# =============================================================================
# Model Import Tests
# =============================================================================


class TestTier2ModelExports:
    """Tests for Tier 2 model exports."""

    def test_tier2_models_importable_from_package(self) -> None:
        """Tier 2 models can be imported from autom8_asana package."""
        from autom8_asana import (
            Attachment,
            Goal,
            GoalMembership,
            GoalMetric,
            Portfolio,
            Story,
            Tag,
            Team,
            TeamMembership,
            Webhook,
            WebhookFilter,
        )

        # Just verify they're importable and are classes
        assert Attachment is not None
        assert Goal is not None
        assert GoalMembership is not None
        assert GoalMetric is not None
        assert Portfolio is not None
        assert Story is not None
        assert Tag is not None
        assert Team is not None
        assert TeamMembership is not None
        assert Webhook is not None
        assert WebhookFilter is not None
