"""Tests for NameResolver.

Per ADR-0060: Name resolution with per-SaveSession caching.
"""

from __future__ import annotations

import pytest

from autom8_asana.clients.name_resolver import NameResolver
from autom8_asana.errors import NameNotFoundError


class MockResource:
    """Mock resource for testing."""

    def __init__(self, gid: str, name: str, email: str | None = None) -> None:
        self.gid = gid
        self.name = name
        self.email = email


class MockAsanaClient:
    """Mock client for testing."""

    def __init__(self) -> None:
        self.default_workspace_gid = "ws_123"
        self._tags = []
        self._sections = []
        self._projects = []
        self._users = []

    async def tags_list_for_workspace(self, workspace_gid: str):
        """Mock async generator for tags."""
        for tag in self._tags:
            yield tag

    async def sections_list_by_project(self, project_gid: str):
        """Mock async generator for sections."""
        for section in self._sections:
            yield section

    async def projects_list_for_workspace(self, workspace_gid: str):
        """Mock async generator for projects."""
        for project in self._projects:
            yield project

    async def users_list_by_workspace(self, workspace_gid: str):
        """Mock async generator for users."""
        for user in self._users:
            yield user


class MockTags:
    """Mock tags interface."""

    def __init__(self, client: MockAsanaClient) -> None:
        self._client = client

    async def list_for_workspace_async(self, workspace_gid: str):
        """List tags for workspace."""
        for tag in self._client._tags:
            yield tag


class MockSections:
    """Mock sections interface."""

    def __init__(self, client: MockAsanaClient) -> None:
        self._client = client

    async def list_for_project_async(self, project_gid: str):
        """List sections by project."""
        for section in self._client._sections:
            yield section


class MockProjects:
    """Mock projects interface."""

    def __init__(self, client: MockAsanaClient) -> None:
        self._client = client

    async def list_async(self, workspace: str):
        """List projects for workspace."""
        for project in self._client._projects:
            yield project


class MockUsers:
    """Mock users interface."""

    def __init__(self, client: MockAsanaClient) -> None:
        self._client = client

    async def list_for_workspace_async(self, workspace_gid: str):
        """List users by workspace."""
        for user in self._client._users:
            yield user


@pytest.fixture
def mock_client() -> MockAsanaClient:
    """Create mock client with all interfaces."""
    client = MockAsanaClient()
    client.tags = MockTags(client)
    client.sections = MockSections(client)
    client.projects = MockProjects(client)
    client.users = MockUsers(client)
    return client


class TestNameResolverTag:
    """Tests for tag resolution."""

    @pytest.mark.asyncio
    async def test_resolve_tag_by_name(self, mock_client: MockAsanaClient) -> None:
        """resolve_tag_async returns GID for matching tag name."""
        mock_client._tags = [
            MockResource(gid="tag_123", name="Urgent"),
            MockResource(gid="tag_456", name="Backlog"),
        ]
        resolver = NameResolver(mock_client)

        gid = await resolver.resolve_tag_async("Urgent")

        assert gid == "tag_123"

    @pytest.mark.asyncio
    async def test_resolve_tag_passthrough_gid(
        self, mock_client: MockAsanaClient
    ) -> None:
        """resolve_tag_async passes through if input looks like GID."""
        resolver = NameResolver(mock_client)

        gid = await resolver.resolve_tag_async("12345678901234567890")

        # Should return as-is without fetching
        assert gid == "12345678901234567890"

    @pytest.mark.asyncio
    async def test_resolve_tag_case_insensitive(
        self, mock_client: MockAsanaClient
    ) -> None:
        """resolve_tag_async matches case-insensitively."""
        mock_client._tags = [MockResource(gid="tag_123", name="Urgent")]
        resolver = NameResolver(mock_client)

        gid = await resolver.resolve_tag_async("urgent")

        assert gid == "tag_123"

    @pytest.mark.asyncio
    async def test_resolve_tag_whitespace_stripped(
        self, mock_client: MockAsanaClient
    ) -> None:
        """resolve_tag_async strips whitespace."""
        mock_client._tags = [MockResource(gid="tag_123", name="Urgent")]
        resolver = NameResolver(mock_client)

        gid = await resolver.resolve_tag_async("  Urgent  ")

        assert gid == "tag_123"

    @pytest.mark.asyncio
    async def test_resolve_tag_not_found_raises(
        self, mock_client: MockAsanaClient
    ) -> None:
        """resolve_tag_async raises NameNotFoundError for missing tag."""
        mock_client._tags = [MockResource(gid="tag_123", name="Urgent")]
        resolver = NameResolver(mock_client)

        with pytest.raises(NameNotFoundError) as exc_info:
            await resolver.resolve_tag_async("NonExistent")

        assert exc_info.value.resource_type == "tag"
        assert exc_info.value.name == "NonExistent"

    @pytest.mark.asyncio
    async def test_resolve_tag_suggests_alternatives(
        self, mock_client: MockAsanaClient
    ) -> None:
        """resolve_tag_async suggests similar names in error."""
        mock_client._tags = [
            MockResource(gid="tag_123", name="Urgent"),
            MockResource(gid="tag_456", name="Backlog"),
        ]
        resolver = NameResolver(mock_client)

        with pytest.raises(NameNotFoundError) as exc_info:
            await resolver.resolve_tag_async("Urgen")  # Typo

        # Should suggest "Urgent"
        assert "Urgent" in exc_info.value.suggestions

    @pytest.mark.asyncio
    async def test_resolve_tag_caches_result(
        self, mock_client: MockAsanaClient
    ) -> None:
        """resolve_tag_async uses cache on second call (no API call)."""
        mock_client._tags = [MockResource(gid="tag_123", name="Urgent")]
        resolver = NameResolver(mock_client)

        # First call
        gid1 = await resolver.resolve_tag_async("Urgent")

        # Clear tags to verify cache is used
        mock_client._tags = []

        # Second call should return cached result
        gid2 = await resolver.resolve_tag_async("Urgent")

        assert gid1 == gid2 == "tag_123"

    @pytest.mark.asyncio
    async def test_resolve_tag_different_caches(
        self, mock_client: MockAsanaClient
    ) -> None:
        """Different resolver instances have different caches."""
        mock_client._tags = [MockResource(gid="tag_123", name="Urgent")]

        resolver1 = NameResolver(mock_client)
        resolver2 = NameResolver(mock_client)

        # Both resolve
        gid1 = await resolver1.resolve_tag_async("Urgent")
        gid2 = await resolver2.resolve_tag_async("Urgent")

        # Same result
        assert gid1 == gid2 == "tag_123"

        # But they have different cache instances
        assert resolver1._cache is not resolver2._cache


class TestNameResolverSection:
    """Tests for section resolution."""

    @pytest.mark.asyncio
    async def test_resolve_section_by_name(self, mock_client: MockAsanaClient) -> None:
        """resolve_section_async returns GID for section in project."""
        mock_client._sections = [
            MockResource(gid="sec_123", name="Backlog"),
            MockResource(gid="sec_456", name="In Progress"),
        ]
        resolver = NameResolver(mock_client)

        gid = await resolver.resolve_section_async("Backlog", "project_789")

        assert gid == "sec_123"

    @pytest.mark.asyncio
    async def test_resolve_section_not_found(
        self, mock_client: MockAsanaClient
    ) -> None:
        """resolve_section_async raises for missing section."""
        mock_client._sections = [MockResource(gid="sec_123", name="Backlog")]
        resolver = NameResolver(mock_client)

        with pytest.raises(NameNotFoundError) as exc_info:
            await resolver.resolve_section_async("NonExistent", "project_789")

        assert exc_info.value.resource_type == "section"

    @pytest.mark.asyncio
    async def test_resolve_section_passthrough_gid(
        self, mock_client: MockAsanaClient
    ) -> None:
        """resolve_section_async passes through GID."""
        resolver = NameResolver(mock_client)

        gid = await resolver.resolve_section_async(
            "12345678901234567890", "project_789"
        )

        assert gid == "12345678901234567890"


class TestNameResolverProject:
    """Tests for project resolution."""

    @pytest.mark.asyncio
    async def test_resolve_project_by_name(self, mock_client: MockAsanaClient) -> None:
        """resolve_project_async returns GID for project in workspace."""
        mock_client._projects = [
            MockResource(gid="proj_123", name="Q4 Planning"),
            MockResource(gid="proj_456", name="Q1 Planning"),
        ]
        resolver = NameResolver(mock_client)

        gid = await resolver.resolve_project_async("Q4 Planning", "ws_789")

        assert gid == "proj_123"

    @pytest.mark.asyncio
    async def test_resolve_project_not_found(
        self, mock_client: MockAsanaClient
    ) -> None:
        """resolve_project_async raises for missing project."""
        mock_client._projects = [MockResource(gid="proj_123", name="Q4 Planning")]
        resolver = NameResolver(mock_client)

        with pytest.raises(NameNotFoundError) as exc_info:
            await resolver.resolve_project_async("NonExistent", "ws_789")

        assert exc_info.value.resource_type == "project"

    @pytest.mark.asyncio
    async def test_resolve_project_passthrough_gid(
        self, mock_client: MockAsanaClient
    ) -> None:
        """resolve_project_async passes through GID."""
        resolver = NameResolver(mock_client)

        gid = await resolver.resolve_project_async("12345678901234567890", "ws_789")

        assert gid == "12345678901234567890"


class TestNameResolverAssignee:
    """Tests for assignee/user resolution."""

    @pytest.mark.asyncio
    async def test_resolve_assignee_by_name(self, mock_client: MockAsanaClient) -> None:
        """resolve_assignee_async matches user by name."""
        mock_client._users = [
            MockResource(gid="user_123", name="Alice", email="alice@example.com"),
        ]
        resolver = NameResolver(mock_client)

        gid = await resolver.resolve_assignee_async("Alice", "ws_789")

        assert gid == "user_123"

    @pytest.mark.asyncio
    async def test_resolve_assignee_by_email(
        self, mock_client: MockAsanaClient
    ) -> None:
        """resolve_assignee_async matches user by email."""
        mock_client._users = [
            MockResource(gid="user_123", name="Alice", email="alice@example.com"),
        ]
        resolver = NameResolver(mock_client)

        gid = await resolver.resolve_assignee_async("alice@example.com", "ws_789")

        assert gid == "user_123"

    @pytest.mark.asyncio
    async def test_resolve_assignee_not_found(
        self, mock_client: MockAsanaClient
    ) -> None:
        """resolve_assignee_async raises for missing user."""
        mock_client._users = [
            MockResource(gid="user_123", name="Alice", email="alice@example.com"),
        ]
        resolver = NameResolver(mock_client)

        with pytest.raises(NameNotFoundError) as exc_info:
            await resolver.resolve_assignee_async("NonExistent", "ws_789")

        assert exc_info.value.resource_type == "user"

    @pytest.mark.asyncio
    async def test_resolve_assignee_case_insensitive_email(
        self, mock_client: MockAsanaClient
    ) -> None:
        """resolve_assignee_async matches email case-insensitively."""
        mock_client._users = [
            MockResource(gid="user_123", name="Alice", email="alice@example.com"),
        ]
        resolver = NameResolver(mock_client)

        gid = await resolver.resolve_assignee_async("ALICE@EXAMPLE.COM", "ws_789")

        assert gid == "user_123"

    @pytest.mark.asyncio
    async def test_resolve_assignee_passthrough_gid(
        self, mock_client: MockAsanaClient
    ) -> None:
        """resolve_assignee_async passes through GID."""
        resolver = NameResolver(mock_client)

        gid = await resolver.resolve_assignee_async("12345678901234567890", "ws_789")

        assert gid == "12345678901234567890"


class TestNameResolverSync:
    """Tests for sync wrappers."""

    def test_resolve_tag_sync(self, mock_client: MockAsanaClient) -> None:
        """resolve_tag (sync) works correctly."""
        mock_client._tags = [MockResource(gid="tag_123", name="Urgent")]
        resolver = NameResolver(mock_client)

        gid = resolver.resolve_tag("Urgent")

        assert gid == "tag_123"

    def test_resolve_section_sync(self, mock_client: MockAsanaClient) -> None:
        """resolve_section (sync) works correctly."""
        mock_client._sections = [MockResource(gid="sec_123", name="Backlog")]
        resolver = NameResolver(mock_client)

        gid = resolver.resolve_section("Backlog", "project_789")

        assert gid == "sec_123"

    def test_resolve_project_sync(self, mock_client: MockAsanaClient) -> None:
        """resolve_project (sync) works correctly."""
        mock_client._projects = [MockResource(gid="proj_123", name="Q4 Planning")]
        resolver = NameResolver(mock_client)

        gid = resolver.resolve_project("Q4 Planning", "ws_789")

        assert gid == "proj_123"

    def test_resolve_assignee_sync(self, mock_client: MockAsanaClient) -> None:
        """resolve_assignee (sync) works correctly."""
        mock_client._users = [
            MockResource(gid="user_123", name="Alice", email="alice@example.com"),
        ]
        resolver = NameResolver(mock_client)

        gid = resolver.resolve_assignee("alice@example.com", "ws_789")

        assert gid == "user_123"


class TestNameResolverLooksLikeGid:
    """Tests for GID detection."""

    def test_looks_like_gid_true_for_20_char_alphanum(self) -> None:
        """_looks_like_gid returns True for 20+ alphanumeric strings."""
        assert NameResolver._looks_like_gid("12345678901234567890")  # 20 chars

    def test_looks_like_gid_true_for_longer_strings(self) -> None:
        """_looks_like_gid returns True for longer alphanumeric strings."""
        assert NameResolver._looks_like_gid("123456789012345678901")  # 21 chars

    def test_looks_like_gid_true_with_underscores(self) -> None:
        """_looks_like_gid returns True for alphanumeric with underscores."""
        assert NameResolver._looks_like_gid(
            "1234567890_1234567890"
        )  # 20 chars with underscore

    def test_looks_like_gid_false_for_short_strings(self) -> None:
        """_looks_like_gid returns False for strings < 20 chars."""
        assert not NameResolver._looks_like_gid("12345")
        assert not NameResolver._looks_like_gid("Urgent")

    def test_looks_like_gid_false_for_non_alphanumeric(self) -> None:
        """_looks_like_gid returns False for non-alphanumeric strings."""
        assert not NameResolver._looks_like_gid("1234567890-1234567890")  # Has dash
        assert not NameResolver._looks_like_gid("1234567890 1234567890")  # Has space

    def test_looks_like_gid_false_for_names(self) -> None:
        """_looks_like_gid returns False for typical names."""
        assert not NameResolver._looks_like_gid("Urgent Task")
        assert not NameResolver._looks_like_gid("Q4 Planning")


class TestNameResolverPerSessionCaching:
    """Tests for per-session caching behavior."""

    @pytest.mark.asyncio
    async def test_cache_populated_on_resolve(
        self, mock_client: MockAsanaClient
    ) -> None:
        """Cache is populated when resolve is called."""
        mock_client._tags = [MockResource(gid="tag_123", name="Urgent")]

        # Resolve without pre-allocated cache
        resolver = NameResolver(mock_client)

        # Resolve
        gid = await resolver.resolve_tag_async("Urgent")

        # Verify result
        assert gid == "tag_123"
        # Verify cache was populated with the resolution
        assert len(resolver._cache) > 0
        assert any("tag" in key for key in resolver._cache)

    @pytest.mark.asyncio
    async def test_cache_hit_prevents_api_call(
        self, mock_client: MockAsanaClient
    ) -> None:
        """Second resolve uses cache and doesn't call API."""
        call_count = {"tags": 0}

        original_list = mock_client.tags.list_for_workspace_async

        async def counting_list(workspace_gid: str):
            call_count["tags"] += 1
            async for item in original_list(workspace_gid):
                yield item

        mock_client._tags = [MockResource(gid="tag_123", name="Urgent")]
        mock_client.tags.list_for_workspace_async = counting_list

        resolver = NameResolver(mock_client)

        # First resolve - calls API
        gid1 = await resolver.resolve_tag_async("Urgent")
        first_count = call_count["tags"]

        # Second resolve - uses cache
        gid2 = await resolver.resolve_tag_async("Urgent")
        second_count = call_count["tags"]

        # API should only be called once
        assert first_count == 1
        assert second_count == 1  # No second call
        assert gid1 == gid2 == "tag_123"
