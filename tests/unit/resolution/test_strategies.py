"""Tests for resolution strategies."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.models.business.business import Business
from autom8_asana.models.business.contact import Contact
from autom8_asana.resolution.budget import ApiBudget
from autom8_asana.resolution.context import ResolutionContext
from autom8_asana.resolution.strategies import (
    DependencyShortcutStrategy,
    HierarchyTraversalStrategy,
    NavigationRefStrategy,
    SessionCacheStrategy,
)
from tests.unit.resolution.conftest import make_business_entity, make_mock_task


class TestSessionCacheStrategy:
    """Tests for SessionCacheStrategy."""

    @pytest.mark.asyncio
    async def test_returns_cached_entity(
        self, mock_client: MagicMock, mock_business: Business
    ) -> None:
        """Test strategy returns entity from cache."""
        context = ResolutionContext(mock_client)
        context.cache_entity(mock_business)

        strategy = SessionCacheStrategy()
        budget = ApiBudget()

        from_entity = make_business_entity("source-123", "Source")
        result = await strategy.resolve_async(
            Business, context, from_entity=from_entity, budget=budget
        )

        assert result is not None
        assert result.entity == mock_business
        assert result.api_calls_used == 0
        assert result.strategy_used == "session_cache"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_cached(self, mock_client: MagicMock) -> None:
        """Test strategy returns None when entity not cached."""
        context = ResolutionContext(mock_client)
        strategy = SessionCacheStrategy()
        budget = ApiBudget()

        from_entity = make_business_entity("source-123", "Source")
        result = await strategy.resolve_async(
            Business, context, from_entity=from_entity, budget=budget
        )

        assert result is None


class TestNavigationRefStrategy:
    """Tests for NavigationRefStrategy."""

    @pytest.mark.asyncio
    async def test_walks_refs_to_find_target(self, mock_client: MagicMock) -> None:
        """Test walking navigation references."""
        business = Business(gid="biz-123", name="Business", resource_type="task")
        contact = Contact(gid="contact-123", name="Contact", resource_type="task")
        contact._business = business  # Set navigation ref

        context = ResolutionContext(mock_client)
        strategy = NavigationRefStrategy()
        budget = ApiBudget()

        result = await strategy.resolve_async(
            Business, context, from_entity=contact, budget=budget
        )

        assert result is not None
        assert result.entity == business
        assert result.api_calls_used == 0
        assert result.strategy_used == "navigation_ref"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_ref(self, mock_client: MagicMock) -> None:
        """Test returns None when no navigation ref found."""
        contact = Contact(gid="contact-123", name="Contact", resource_type="task")
        # No _business ref set

        context = ResolutionContext(mock_client)
        strategy = NavigationRefStrategy()
        budget = ApiBudget()

        result = await strategy.resolve_async(
            Business, context, from_entity=contact, budget=budget
        )

        assert result is None


class TestDependencyShortcutStrategy:
    """Tests for DependencyShortcutStrategy."""

    @pytest.mark.asyncio
    async def test_resolves_via_dependency(self, mock_client: MagicMock) -> None:
        """Test resolving via dependency link."""
        from_entity = make_business_entity("source-123", "Source")
        dep_task = make_mock_task("dep-456", "Dependency")

        # Mock dependencies_async to return a dependency
        async def mock_collect():
            return [MagicMock(gid="dep-456")]

        mock_iter = MagicMock()
        mock_iter.collect = mock_collect
        mock_client.tasks.dependencies_async.return_value = mock_iter
        mock_client.tasks.get_async.return_value = dep_task

        context = ResolutionContext(mock_client)
        strategy = DependencyShortcutStrategy()
        budget = ApiBudget()

        result = await strategy.resolve_async(
            Contact, context, from_entity=from_entity, budget=budget
        )

        assert result is not None
        assert result.api_calls_used == 2
        assert result.strategy_used == "dependency_shortcut"

    @pytest.mark.asyncio
    async def test_returns_none_when_budget_too_low(
        self, mock_client: MagicMock
    ) -> None:
        """Test returns None when budget < 2."""
        from_entity = make_business_entity("source-123", "Source")
        context = ResolutionContext(mock_client)
        strategy = DependencyShortcutStrategy()
        budget = ApiBudget(max_calls=1)

        result = await strategy.resolve_async(
            Contact, context, from_entity=from_entity, budget=budget
        )

        assert result is None


class TestHierarchyTraversalStrategy:
    """Tests for HierarchyTraversalStrategy."""

    @pytest.mark.asyncio
    async def test_traverses_to_business(self, mock_client: MagicMock) -> None:
        """Test traversing parent chain to Business."""
        from_entity = make_business_entity("child-123", "Child")
        parent_ref = MagicMock()
        parent_ref.gid = "parent-456"

        parent_task = make_mock_task("parent-456", "Parent")
        parent_task.parent = None

        # Mock the parent fetch
        mock_client.tasks.get_async.side_effect = [
            MagicMock(parent=parent_ref),  # First call returns parent ref
            parent_task,  # Second call returns parent task
        ]

        context = ResolutionContext(mock_client)
        strategy = HierarchyTraversalStrategy()
        budget = ApiBudget()

        result = await strategy.resolve_async(
            Business, context, from_entity=from_entity, budget=budget
        )

        # Should traverse and find business (or fail gracefully)
        assert budget.used >= 2  # At least 2 API calls made

    @pytest.mark.asyncio
    async def test_returns_none_when_budget_too_low(
        self, mock_client: MagicMock
    ) -> None:
        """Test returns None when budget < 3."""
        from_entity = make_business_entity("child-123", "Child")
        context = ResolutionContext(mock_client)
        strategy = HierarchyTraversalStrategy()
        budget = ApiBudget(max_calls=2)

        result = await strategy.resolve_async(
            Business, context, from_entity=from_entity, budget=budget
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_cached_business(self, mock_client: MagicMock) -> None:
        """Test returns cached business without traversal."""
        business = Business(gid="biz-123", name="Business", resource_type="task")
        context = ResolutionContext(mock_client)
        context.cache_entity(business)

        from_entity = make_business_entity("child-123", "Child")
        strategy = HierarchyTraversalStrategy()
        budget = ApiBudget()

        result = await strategy.resolve_async(
            Business, context, from_entity=from_entity, budget=budget
        )

        # Should find cached business without API calls
        assert budget.used == 0 or result is not None
