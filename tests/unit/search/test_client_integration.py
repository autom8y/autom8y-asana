"""Tests for AsanaClient.search integration.

Per TDD-search-interface: Verifies SearchService wiring into AsanaClient.
"""

from __future__ import annotations

from autom8_asana._defaults.cache import InMemoryCacheProvider
from autom8_asana.client import AsanaClient
from autom8_asana.search import SearchService


class TestClientSearchProperty:
    """Tests for AsanaClient.search property."""

    def test_search_property_returns_search_service(self) -> None:
        """AsanaClient.search should return SearchService instance."""
        client = AsanaClient(
            token="test_token",
            workspace_gid="test_workspace",
        )
        search = client.search
        assert isinstance(search, SearchService)

    def test_search_property_lazy_initialized(self) -> None:
        """Search property should be lazily initialized."""
        client = AsanaClient(
            token="test_token",
            workspace_gid="test_workspace",
        )
        # Private attribute should be None before first access
        assert client._search is None
        # Access property
        _ = client.search
        # Now it should be set
        assert client._search is not None

    def test_search_property_same_instance(self) -> None:
        """Search property should return same instance on multiple accesses."""
        client = AsanaClient(
            token="test_token",
            workspace_gid="test_workspace",
        )
        search1 = client.search
        search2 = client.search
        assert search1 is search2

    def test_search_property_with_custom_cache(self) -> None:
        """Search should use client's cache provider."""
        cache = InMemoryCacheProvider(default_ttl=300, max_size=1000)
        client = AsanaClient(
            token="test_token",
            workspace_gid="test_workspace",
            cache_provider=cache,
        )
        search = client.search
        assert search._cache is cache
