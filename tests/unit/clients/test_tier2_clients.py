"""Tests for Tier 2 Resource Clients (TDD-0004).

Tests WebhooksClient, TeamsClient, AttachmentsClient, TagsClient,
GoalsClient, PortfoliosClient, and StoriesClient.
Follows Tier 1 test patterns with mocked HTTP dependencies.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import tempfile
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from autom8_asana.clients.attachments import AttachmentsClient
from autom8_asana.clients.goals import GoalsClient
from autom8_asana.clients.portfolios import PortfoliosClient
from autom8_asana.clients.stories import StoriesClient
from autom8_asana.clients.tags import TagsClient
from autom8_asana.clients.teams import TeamsClient
from autom8_asana.clients.webhooks import WebhooksClient
from autom8_asana.errors import AsanaError
from autom8_asana.models import (
    Attachment,
    Goal,
    PageIterator,
    Portfolio,
    Story,
    Tag,
    Team,
    Webhook,
)
from autom8_asana.models.goal import GoalMetric
from autom8_asana.models.team import TeamMembership

if TYPE_CHECKING:
    from autom8_asana.config import AsanaConfig


# =============================================================================
# Cross-Client Parametrized Tests (Pattern A per CRU-S3 TDD)
# =============================================================================


def _check_webhook(result: Webhook) -> None:
    assert result.target == "https://example.com/webhook"
    assert result.active is True


def _check_team(result: Team) -> None:
    assert result.name == "Engineering"


def _check_tag(result: Tag) -> None:
    assert result.name == "Priority"
    assert result.color == "dark-red"


def _check_story(result: Story) -> None:
    assert result.resource_subtype == "comment_added"
    assert result.text == "This is a comment"


def _check_attachment(result: Attachment) -> None:
    assert result.name == "report.pdf"
    assert result.size == 1024


def _check_goal(result: Goal) -> None:
    assert result.name == "Q4 Revenue Target"
    assert result.status == "on_track"


def _check_portfolio(result: Portfolio) -> None:
    assert result.name == "Q4 Projects"


@pytest.mark.parametrize(
    ("client_cls", "gid", "payload", "expected_model", "url_template", "extra_check"),
    [
        (
            WebhooksClient,
            "wh123",
            {
                "gid": "wh123",
                "target": "https://example.com/webhook",
                "active": True,
            },
            Webhook,
            "/webhooks/{gid}",
            _check_webhook,
        ),
        (
            TeamsClient,
            "team123",
            {
                "gid": "team123",
                "name": "Engineering",
                "organization": {"gid": "org1", "name": "Acme Corp"},
            },
            Team,
            "/teams/{gid}",
            _check_team,
        ),
        (
            TagsClient,
            "tag123",
            {"gid": "tag123", "name": "Priority", "color": "dark-red"},
            Tag,
            "/tags/{gid}",
            _check_tag,
        ),
        (
            StoriesClient,
            "story123",
            {
                "gid": "story123",
                "resource_subtype": "comment_added",
                "text": "This is a comment",
                "created_by": {"gid": "user1", "name": "Alice"},
            },
            Story,
            "/stories/{gid}",
            _check_story,
        ),
        (
            AttachmentsClient,
            "att123",
            {"gid": "att123", "name": "report.pdf", "size": 1024, "host": "asana"},
            Attachment,
            "/attachments/{gid}",
            _check_attachment,
        ),
        (
            GoalsClient,
            "goal123",
            {"gid": "goal123", "name": "Q4 Revenue Target", "status": "on_track"},
            Goal,
            "/goals/{gid}",
            _check_goal,
        ),
        (
            PortfoliosClient,
            "port123",
            {
                "gid": "port123",
                "name": "Q4 Projects",
                "owner": {"gid": "user1", "name": "Alice"},
            },
            Portfolio,
            "/portfolios/{gid}",
            _check_portfolio,
        ),
    ],
    ids=[
        "webhooks_get",
        "teams_get",
        "tags_get",
        "stories_get",
        "attachments_get",
        "goals_get",
        "portfolios_get",
    ],
)
async def test_tier2_get_async_returns_model(
    client_factory,
    mock_http,
    client_cls,
    gid,
    payload,
    expected_model,
    url_template,
    extra_check,
) -> None:
    """get_async returns the typed model for each tier-2 client.

    Consolidates the seven previously-copy-pasted
    ``test_get_async_returns_*_model`` tests (Webhooks, Teams, Tags, Stories,
    Attachments, Goals, Portfolios). Webhook has no ``name`` so its extra_check
    validates ``target`` + ``active`` instead.
    """
    client = client_factory(client_cls, use_cache=False)
    mock_http.get.return_value = payload

    result = await client.get_async(gid)

    assert isinstance(result, expected_model)
    assert result.gid == payload["gid"]
    extra_check(result)

    mock_http.get.assert_called_once_with(url_template.format(gid=gid), params={})


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
            json={"data": {"resource": "proj123", "target": "https://example.com/webhook"}},
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

        result = await tags_client.create_async(workspace="ws1", name="Priority", color="dark-blue")

        assert isinstance(result, Tag)
        assert result.gid == "tag123"
        mock_http.post.assert_called_once_with(
            "/tags",
            json={"data": {"workspace": "ws1", "name": "Priority", "color": "dark-blue"}},
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

        result = await stories_client.create_comment_async(task="task1", text="Great work!")

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


# =============================================================================
# Webhook Security Tests (merged from test_tier2_adversarial.py)
# Per ADR-0008: HMAC-SHA256 with timing-safe comparison.
# =============================================================================


class TestWebhookSignatureVerificationValid:
    """Tests for valid webhook signature verification."""

    def test_verify_signature_valid_empty_body(self) -> None:
        """verify_signature handles empty request body."""
        secret = "test_secret"
        body = b""
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        result = WebhooksClient.verify_signature(body, expected, secret)
        assert result is True

    def test_verify_signature_valid_json_body(self) -> None:
        """verify_signature validates standard JSON body."""
        secret = "my_webhook_secret_123"
        body = b'{"events":[{"resource":{"gid":"123"}}]}'
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        result = WebhooksClient.verify_signature(body, expected, secret)
        assert result is True

    def test_verify_signature_valid_large_body(self) -> None:
        """verify_signature handles large request bodies."""
        secret = "secret"
        body = b"x" * 1_000_000  # 1MB body
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        result = WebhooksClient.verify_signature(body, expected, secret)
        assert result is True

    def test_verify_signature_valid_binary_body(self) -> None:
        """verify_signature handles binary data in body."""
        secret = "secret"
        body = bytes(range(256))  # All possible byte values
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        result = WebhooksClient.verify_signature(body, expected, secret)
        assert result is True


class TestWebhookSignatureVerificationInvalid:
    """Tests for invalid webhook signature rejection."""

    def test_verify_signature_invalid_wrong_signature(self) -> None:
        """verify_signature rejects wrong signature."""
        result = WebhooksClient.verify_signature(
            b'{"events": []}',
            "completely_wrong_signature",
            "test_secret",
        )
        assert result is False

    def test_verify_signature_invalid_truncated_signature(self) -> None:
        """verify_signature rejects truncated signature."""
        secret = "test_secret"
        body = b'{"test": "data"}'
        correct = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        truncated = correct[:32]  # Half the signature

        result = WebhooksClient.verify_signature(body, truncated, secret)
        assert result is False

    def test_verify_signature_invalid_wrong_secret(self) -> None:
        """verify_signature rejects signature computed with wrong secret."""
        body = b'{"test": "data"}'
        wrong_sig = hmac.new(b"wrong_secret", body, hashlib.sha256).hexdigest()

        result = WebhooksClient.verify_signature(body, wrong_sig, "correct_secret")
        assert result is False

    def test_verify_signature_invalid_modified_body(self) -> None:
        """verify_signature rejects signature when body was modified."""
        secret = "test_secret"
        original_body = b'{"events": []}'
        sig = hmac.new(secret.encode(), original_body, hashlib.sha256).hexdigest()

        # Attacker modifies body
        modified_body = b'{"events": [{"malicious": true}]}'

        result = WebhooksClient.verify_signature(modified_body, sig, secret)
        assert result is False

    def test_verify_signature_invalid_empty_signature(self) -> None:
        """verify_signature rejects empty signature."""
        result = WebhooksClient.verify_signature(
            b'{"events": []}',
            "",
            "test_secret",
        )
        assert result is False

    def test_verify_signature_invalid_case_sensitivity(self) -> None:
        """verify_signature is case-sensitive for hex signatures."""
        secret = "test_secret"
        body = b'{"test": "data"}'
        sig_lower = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        sig_upper = sig_lower.upper()

        # Lowercase is valid
        assert WebhooksClient.verify_signature(body, sig_lower, secret) is True
        # Uppercase should fail (compare_digest compares exact strings)
        assert WebhooksClient.verify_signature(body, sig_upper, secret) is False


class TestWebhookSignatureTimingSafety:
    """Tests to verify timing-safe comparison (hmac.compare_digest) is used."""

    def test_partial_match_rejected(self) -> None:
        """Verify partial signature matches are rejected."""
        secret = "test"
        body = b"data"
        correct_sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        # Try various partial matches that could pass with naive comparison
        assert WebhooksClient.verify_signature(body, correct_sig[:-1], secret) is False
        assert WebhooksClient.verify_signature(body, correct_sig + "x", secret) is False
        assert WebhooksClient.verify_signature(body, "0" + correct_sig[1:], secret) is False


class TestWebhookHandshakeSecretExtractionAdversarial:
    """Adversarial tests for extracting handshake secrets from headers."""

    def test_extract_handshake_secret_mixed_case(self) -> None:
        """Extract secret with mixed case header."""
        headers = {"X-HOOK-SECRET": "secret_789"}
        result = WebhooksClient.extract_handshake_secret(headers)
        assert result == "secret_789"

    def test_extract_handshake_secret_with_other_headers(self) -> None:
        """Extract secret when other headers are present."""
        headers = {
            "Content-Type": "application/json",
            "X-Hook-Secret": "the_secret",
            "User-Agent": "Asana-Webhooks",
            "X-Hook-Signature": "some_signature",
        }
        result = WebhooksClient.extract_handshake_secret(headers)
        assert result == "the_secret"

    def test_extract_handshake_secret_empty_headers(self) -> None:
        """Return None for empty headers dict."""
        headers: dict[str, str] = {}
        result = WebhooksClient.extract_handshake_secret(headers)
        assert result is None

    def test_extract_handshake_secret_empty_value(self) -> None:
        """Return empty string if secret value is empty."""
        headers = {"X-Hook-Secret": ""}
        result = WebhooksClient.extract_handshake_secret(headers)
        assert result == ""


# =============================================================================
# Attachment Edge Cases (merged from test_tier2_adversarial.py)
# =============================================================================


class TestAttachmentUploadEdgeCases:
    """Tests for attachment upload edge cases."""

    async def test_upload_empty_file(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """Upload handles empty file correctly."""
        mock_http.post_multipart.return_value = {
            "gid": "att123",
            "name": "empty.txt",
            "size": 0,
        }

        file_obj = BytesIO(b"")
        result = await attachments_client.upload_async(
            parent="task1", file=file_obj, name="empty.txt"
        )

        assert isinstance(result, Attachment)
        assert result.size == 0
        mock_http.post_multipart.assert_called_once()

    async def test_upload_various_file_types(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """Upload handles various MIME types correctly."""
        test_cases = [
            ("document.pdf", "application/pdf"),
            ("image.png", "image/png"),
            ("image.jpg", "image/jpeg"),
            ("data.json", "application/json"),
            ("archive.zip", "application/zip"),
            ("unknown.randomext123", "application/octet-stream"),  # Unknown extension
        ]

        for filename, expected_mime in test_cases:
            mock_http.post_multipart.reset_mock()
            mock_http.post_multipart.return_value = {
                "gid": "att123",
                "name": filename,
            }

            file_obj = BytesIO(b"test content")
            await attachments_client.upload_async(parent="task1", file=file_obj, name=filename)

            call_args = mock_http.post_multipart.call_args
            files_param = call_args[1]["files"]
            # files is {"file": (name, file_obj, content_type)}  # noqa: ERA001
            actual_mime = files_param["file"][2]
            assert actual_mime == expected_mime, f"Failed for {filename}"

    async def test_upload_explicit_content_type(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """Upload uses explicit content_type when provided."""
        mock_http.post_multipart.return_value = {"gid": "att123", "name": "data.bin"}

        file_obj = BytesIO(b"binary data")
        await attachments_client.upload_async(
            parent="task1",
            file=file_obj,
            name="data.bin",
            content_type="application/custom-type",
        )

        call_args = mock_http.post_multipart.call_args
        files_param = call_args[1]["files"]
        assert files_param["file"][2] == "application/custom-type"


class TestAttachmentUploadFromPath:
    """Tests for upload_from_path_async edge cases."""

    async def test_upload_from_path_uses_basename(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """upload_from_path_async uses path basename by default."""
        mock_http.post_multipart.return_value = {
            "gid": "att123",
            "name": "test.txt",
            "size": 12,
        }

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            result = await attachments_client.upload_from_path_async(parent="task1", path=temp_path)

            assert isinstance(result, Attachment)
            call_args = mock_http.post_multipart.call_args
            files_param = call_args[1]["files"]
            assert files_param["file"][0] == Path(temp_path).name
        finally:
            os.unlink(temp_path)

    async def test_upload_from_path_custom_name(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """upload_from_path_async allows custom name."""
        mock_http.post_multipart.return_value = {
            "gid": "att123",
            "name": "custom_name.pdf",
        }

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            f.write(b"content")
            temp_path = f.name

        try:
            result = await attachments_client.upload_from_path_async(
                parent="task1", path=temp_path, name="custom_name.pdf"
            )

            assert isinstance(result, Attachment)
            call_args = mock_http.post_multipart.call_args
            files_param = call_args[1]["files"]
            assert files_param["file"][0] == "custom_name.pdf"
        finally:
            os.unlink(temp_path)


class TestAttachmentDownload:
    """Tests for attachment download operations."""

    async def test_download_to_path(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """Download attachment to file path."""
        mock_http.get.return_value = {
            "gid": "att123",
            "name": "test.txt",
            "download_url": "https://example.com/download/test.txt",
        }

        async def mock_stream(url: str):
            yield b"chunk1"
            yield b"chunk2"

        mock_http.get_stream_url = mock_stream

        with tempfile.TemporaryDirectory() as tmpdir:
            dest_path = Path(tmpdir) / "downloaded.txt"

            result = await attachments_client.download_async("att123", destination=dest_path)

            assert result == dest_path
            assert dest_path.exists()
            assert dest_path.read_bytes() == b"chunk1chunk2"

    async def test_download_to_file_object(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """Download attachment to file-like object."""
        mock_http.get.return_value = {
            "gid": "att123",
            "name": "test.bin",
            "download_url": "https://example.com/download",
        }

        async def mock_stream(url: str):
            yield b"data"

        mock_http.get_stream_url = mock_stream

        buffer = BytesIO()
        result = await attachments_client.download_async("att123", destination=buffer)

        assert result is None  # None when destination is file object
        assert buffer.getvalue() == b"data"

    async def test_download_no_download_url_raises_error(
        self, attachments_client: AttachmentsClient, mock_http: MockHTTPClient
    ) -> None:
        """Download raises error when no download_url."""
        mock_http.get.return_value = {
            "gid": "att123",
            "name": "external_link",
            "download_url": None,  # External links don't have download URLs
        }

        with pytest.raises(AsanaError) as exc_info:
            await attachments_client.download_async("att123", destination="/tmp/test.txt")

        assert "no download URL" in str(exc_info.value)


# =============================================================================
# Goals Hierarchy Tests (merged from test_tier2_adversarial.py)
# =============================================================================


class TestGoalsSubgoalPositioning:
    """Tests for Goals subgoal positioning operations."""

    async def test_add_subgoal_with_positioning(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Add subgoal with insert_before/after positioning."""
        mock_http.post.return_value = {"gid": "parent", "name": "Parent"}

        # Test insert_before
        await goals_client.add_subgoal_async(
            "parent", subgoal="new_sub", insert_before="existing_sub"
        )

        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["insert_before"] == "existing_sub"

        # Test insert_after
        mock_http.post.reset_mock()
        mock_http.post.return_value = {"gid": "parent", "name": "Parent"}
        await goals_client.add_subgoal_async(
            "parent", subgoal="new_sub", insert_after="existing_sub"
        )

        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["insert_after"] == "existing_sub"

    async def test_remove_subgoal(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Remove subgoal from parent goal."""
        mock_http.post.return_value = {}

        await goals_client.remove_subgoal_async("parent", subgoal="subgoal123")

        mock_http.post.assert_called_once_with(
            "/goals/parent/removeSubgoal",
            json={"data": {"subgoal": "subgoal123"}},
        )

    async def test_list_subgoals_returns_page_iterator(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """list_subgoals_async returns PageIterator[Goal]."""
        mock_http.get_paginated.return_value = (
            [
                {"gid": "sub1", "name": "Subgoal 1"},
                {"gid": "sub2", "name": "Subgoal 2"},
            ],
            None,
        )

        iterator = goals_client.list_subgoals_async("parent_goal")
        assert isinstance(iterator, PageIterator)

        items = await iterator.collect()
        assert len(items) == 2
        assert all(isinstance(g, Goal) for g in items)


class TestGoalsSupportingWork:
    """Tests for Goals supporting work operations."""

    async def test_add_supporting_work_project(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Add project as supporting work to goal."""
        mock_http.post.return_value = {"gid": "goal123", "name": "Goal"}

        result = await goals_client.add_supporting_work_async(
            "goal123", supporting_resource="project456"
        )

        assert isinstance(result, Goal)
        mock_http.post.assert_called_once_with(
            "/goals/goal123/addSupportingRelationship",
            json={"data": {"supporting_resource": "project456"}},
        )

    async def test_add_supporting_work_weight_boundary_values(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Test contribution weight boundary values."""
        mock_http.post.return_value = {"gid": "goal123", "name": "Goal"}

        # Test weight = 0.0
        await goals_client.add_supporting_work_async(
            "goal123", supporting_resource="proj1", contribution_weight=0.0
        )
        assert mock_http.post.call_args[1]["json"]["data"]["contribution_weight"] == 0.0

        # Test weight = 1.0
        mock_http.post.reset_mock()
        mock_http.post.return_value = {"gid": "goal123", "name": "Goal"}
        await goals_client.add_supporting_work_async(
            "goal123", supporting_resource="proj1", contribution_weight=1.0
        )
        assert mock_http.post.call_args[1]["json"]["data"]["contribution_weight"] == 1.0

    async def test_remove_supporting_work(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Remove supporting work from goal."""
        mock_http.post.return_value = {}

        await goals_client.remove_supporting_work_async("goal123", supporting_resource="project456")

        mock_http.post.assert_called_once_with(
            "/goals/goal123/removeSupportingRelationship",
            json={"data": {"supporting_resource": "project456"}},
        )


class TestGoalsFollowers:
    """Tests for Goals follower operations."""

    async def test_add_followers_multiple(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Add multiple followers to goal with comma-join."""
        mock_http.post.return_value = {"gid": "goal123", "name": "Goal"}

        await goals_client.add_followers_async("goal123", followers=["user1", "user2", "user3"])

        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["followers"] == "user1,user2,user3"

    async def test_add_followers_empty_list(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Add empty list of followers (edge case)."""
        mock_http.post.return_value = {"gid": "goal123", "name": "Goal"}

        await goals_client.add_followers_async("goal123", followers=[])

        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["followers"] == ""

    async def test_remove_followers(
        self, goals_client: GoalsClient, mock_http: MockHTTPClient
    ) -> None:
        """Remove followers from goal."""
        mock_http.post.return_value = {"gid": "goal123", "name": "Goal"}

        await goals_client.remove_followers_async("goal123", followers=["user1", "user2"])

        mock_http.post.assert_called_once_with(
            "/goals/goal123/removeFollowers",
            json={"data": {"followers": "user1,user2"}},
        )


class TestGoalsMetricHandling:
    """Tests for Goals with metric values."""

    def test_goal_metric_boundary_values(self) -> None:
        """GoalMetric handles boundary values."""
        # Zero values
        metric = GoalMetric.model_validate(
            {
                "gid": "m1",
                "current_number_value": 0,
                "target_number_value": 0,
            }
        )
        assert metric.current_number_value == 0

        # Large values
        metric = GoalMetric.model_validate(
            {
                "gid": "m2",
                "current_number_value": 1_000_000_000,
                "target_number_value": 1_000_000_000,
            }
        )
        assert metric.current_number_value == 1_000_000_000

        # Negative values (some metrics allow this)
        metric = GoalMetric.model_validate(
            {
                "gid": "m3",
                "current_number_value": -50.5,
                "target_number_value": 100.0,
            }
        )
        assert metric.current_number_value == -50.5

        # Float precision
        metric = GoalMetric.model_validate(
            {
                "gid": "m4",
                "current_number_value": 0.123456789,
            }
        )
        assert metric.current_number_value == 0.123456789


# =============================================================================
# Portfolio Operations (merged from test_tier2_adversarial.py)
# =============================================================================


class TestPortfoliosItemManagement:
    """Tests for Portfolio item (project) management."""

    async def test_add_item_with_positioning(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """Add item with insert_before/insert_after positioning options."""
        mock_http.post.return_value = {}

        await portfolios_client.add_item_async(
            "port123",
            item="proj_new",
            insert_before="proj_existing",
        )

        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["insert_before"] == "proj_existing"

        mock_http.post.reset_mock()
        mock_http.post.return_value = {}
        await portfolios_client.add_item_async(
            "port123",
            item="proj_new",
            insert_after="proj_existing",
        )

        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["insert_after"] == "proj_existing"

    async def test_remove_item(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """Remove project from portfolio."""
        mock_http.post.return_value = {}

        await portfolios_client.remove_item_async("port123", item="project456")

        mock_http.post.assert_called_once_with(
            "/portfolios/port123/removeItem",
            json={"data": {"item": "project456"}},
        )


class TestPortfoliosMemberManagement:
    """Tests for Portfolio member management."""

    async def test_add_members_multiple(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """Add multiple members to portfolio with comma-join."""
        mock_http.post.return_value = {"gid": "port123", "name": "Portfolio"}

        await portfolios_client.add_members_async("port123", members=["user1", "user2", "user3"])

        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["members"] == "user1,user2,user3"

    async def test_remove_members(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """Remove members from portfolio."""
        mock_http.post.return_value = {"gid": "port123", "name": "Portfolio"}

        await portfolios_client.remove_members_async("port123", members=["user1", "user2"])

        mock_http.post.assert_called_once_with(
            "/portfolios/port123/removeMembers",
            json={"data": {"members": "user1,user2"}},
        )


class TestPortfoliosCustomFieldSettings:
    """Tests for Portfolio custom field settings."""

    async def test_add_custom_field_setting(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """Add custom field to portfolio."""
        mock_http.post.return_value = {}

        await portfolios_client.add_custom_field_setting_async("port123", custom_field="cf456")

        mock_http.post.assert_called_once_with(
            "/portfolios/port123/addCustomFieldSetting",
            json={"data": {"custom_field": "cf456"}},
        )

    async def test_add_custom_field_setting_with_importance(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """Add custom field with is_important flag."""
        mock_http.post.return_value = {}

        await portfolios_client.add_custom_field_setting_async(
            "port123", custom_field="cf456", is_important=True
        )

        call_data = mock_http.post.call_args[1]["json"]["data"]
        assert call_data["is_important"] is True

    async def test_remove_custom_field_setting(
        self, portfolios_client: PortfoliosClient, mock_http: MockHTTPClient
    ) -> None:
        """Remove custom field from portfolio."""
        mock_http.post.return_value = {}

        await portfolios_client.remove_custom_field_setting_async("port123", custom_field="cf456")

        mock_http.post.assert_called_once_with(
            "/portfolios/port123/removeCustomFieldSetting",
            json={"data": {"custom_field": "cf456"}},
        )
