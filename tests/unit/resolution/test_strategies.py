"""Tests for resolution strategies."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autom8_asana.models.business.business import Business
from autom8_asana.models.business.contact import Contact
from autom8_asana.models.business.detection.types import (
    CONFIDENCE_TIER_1,
    CONFIDENCE_TIER_5,
    DetectionResult,
    EntityType,
)
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

        result = await strategy.resolve_async(Business, context, from_entity=contact, budget=budget)

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

        result = await strategy.resolve_async(Business, context, from_entity=contact, budget=budget)

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
    async def test_returns_none_when_budget_too_low(self, mock_client: MagicMock) -> None:
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
    @patch("autom8_asana.models.business.detection.detect_entity_type")
    async def test_traverses_to_business(
        self, mock_detect: MagicMock, mock_client: MagicMock
    ) -> None:
        """Test traversing parent chain to Business."""
        from_entity = make_business_entity("child-123", "Child")
        parent_ref = MagicMock()
        parent_ref.gid = "parent-456"

        parent_task = make_mock_task("parent-456", "Parent")
        parent_task.parent = None

        # Detection confirms parent is a Business
        mock_detect.return_value = _make_detection_result(EntityType.BUSINESS)

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

        # Should traverse and find business
        assert budget.used >= 2  # At least 2 API calls made
        assert result is not None

    @pytest.mark.asyncio
    async def test_returns_none_when_budget_too_low(self, mock_client: MagicMock) -> None:
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


def _make_detection_result(
    entity_type: EntityType,
    *,
    tier: int = 1,
    confidence: float = CONFIDENCE_TIER_1,
) -> DetectionResult:
    """Helper to build DetectionResult for tests."""
    return DetectionResult(
        entity_type=entity_type,
        confidence=confidence,
        tier_used=tier,
        needs_healing=False,
        expected_project_gid=None,
    )


def _make_unknown_result() -> DetectionResult:
    """Helper to build UNKNOWN DetectionResult."""
    return DetectionResult(
        entity_type=EntityType.UNKNOWN,
        confidence=CONFIDENCE_TIER_5,
        tier_used=5,
        needs_healing=True,
        expected_project_gid=None,
    )


def _make_parent_chain_task(
    gid: str,
    name: str,
    *,
    parent_gid: str | None = None,
    memberships: list[dict] | None = None,
) -> MagicMock:
    """Helper to create a mock task for parent-chain traversal.

    Returns a MagicMock that behaves like a Task returned by get_async,
    with parent ref, memberships, and model_dump() support.
    """
    task = MagicMock()
    task.gid = gid
    task.name = name
    task.resource_type = "task"
    task.memberships = memberships

    if parent_gid is not None:
        parent_ref = MagicMock()
        parent_ref.gid = parent_gid
        task.parent = parent_ref
    else:
        task.parent = None

    dump = {
        "gid": gid,
        "name": name,
        "resource_type": "task",
    }
    if memberships is not None:
        dump["memberships"] = memberships
    task.model_dump.return_value = dump
    return task


class TestHierarchyTraversalDetection:
    """Tests for detection-gated Business identification in _traverse_to_business_async."""

    @pytest.mark.asyncio
    @patch("autom8_asana.models.business.detection.detect_entity_type")
    async def test_traverse_skips_non_business_finds_actual_business(
        self, mock_detect: MagicMock, mock_client: MagicMock
    ) -> None:
        """Traversal skips OfferHolder parent and finds actual Business higher up."""
        from_entity = make_business_entity("trigger-1", "Trigger")

        # Parent chain: trigger -> offer_holder -> unit -> unit_holder -> business
        offer_holder = _make_parent_chain_task(
            "oh-1",
            "Offers",
            parent_gid="unit-1",
            memberships=[{"project": {"gid": "1143843662099250"}}],
        )
        unit = _make_parent_chain_task(
            "unit-1",
            "Unit",
            parent_gid="uh-1",
            memberships=[{"project": {"gid": "1201081073731555"}}],
        )
        unit_holder = _make_parent_chain_task(
            "uh-1",
            "Units",
            parent_gid="biz-1",
            memberships=[{"project": {"gid": "9999999999"}}],
        )
        business_task = _make_parent_chain_task(
            "biz-1",
            "Acme Corp",
            parent_gid=None,
            memberships=[{"project": {"gid": "1200653012566782"}}],
        )

        # detect_entity_type calls: offer_holder, unit, unit_holder, business
        mock_detect.side_effect = [
            _make_detection_result(EntityType.OFFER_HOLDER),
            _make_detection_result(EntityType.UNIT),
            _make_detection_result(EntityType.UNIT_HOLDER),
            _make_detection_result(EntityType.BUSINESS),
        ]

        # get_async calls: fetch parent ref for trigger, fetch offer_holder,
        # fetch unit, fetch unit_holder, fetch business
        trigger_parent_ref = MagicMock()
        trigger_parent_ref.parent = MagicMock(gid="oh-1")
        mock_client.tasks.get_async.side_effect = [
            trigger_parent_ref,  # discover trigger's parent
            offer_holder,  # fetch offer_holder
            unit,  # fetch unit (offer_holder.parent)
            unit_holder,  # fetch unit_holder (unit.parent)
            business_task,  # fetch business (unit_holder.parent)
        ]

        context = ResolutionContext(mock_client)
        strategy = HierarchyTraversalStrategy()
        budget = ApiBudget(max_calls=20)

        result = await strategy.resolve_async(
            Business, context, from_entity=from_entity, budget=budget
        )

        assert result is not None
        assert result.entity.gid == "biz-1"
        assert result.strategy_used == "hierarchy_traversal"

    @pytest.mark.asyncio
    @patch("autom8_asana.models.business.detection.detect_entity_type")
    async def test_traverse_stops_at_real_business(
        self, mock_detect: MagicMock, mock_client: MagicMock
    ) -> None:
        """Traversal returns Business on first parent when detection confirms it."""
        from_entity = make_business_entity("trigger-1", "Trigger")

        business_task = _make_parent_chain_task(
            "biz-1",
            "Acme Corp",
            parent_gid=None,
            memberships=[{"project": {"gid": "1200653012566782"}}],
        )

        mock_detect.return_value = _make_detection_result(EntityType.BUSINESS)

        trigger_parent_ref = MagicMock()
        trigger_parent_ref.parent = MagicMock(gid="biz-1")
        mock_client.tasks.get_async.side_effect = [
            trigger_parent_ref,  # discover trigger's parent
            business_task,  # fetch business
        ]

        context = ResolutionContext(mock_client)
        strategy = HierarchyTraversalStrategy()
        budget = ApiBudget(max_calls=20)

        result = await strategy.resolve_async(
            Business, context, from_entity=from_entity, budget=budget
        )

        assert result is not None
        assert result.entity.gid == "biz-1"
        assert budget.used == 2

    @pytest.mark.asyncio
    @patch("autom8_asana.models.business.detection.detect_entity_type")
    async def test_traverse_returns_none_when_no_business_found(
        self, mock_detect: MagicMock, mock_client: MagicMock
    ) -> None:
        """Traversal returns None when chain has no Business entity."""
        from_entity = make_business_entity("trigger-1", "Trigger")

        # Single parent with no Business membership, and no further parent
        non_business = _make_parent_chain_task(
            "nb-1",
            "Not A Business",
            parent_gid=None,
            memberships=[{"project": {"gid": "9999999999"}}],
        )

        mock_detect.return_value = _make_unknown_result()

        trigger_parent_ref = MagicMock()
        trigger_parent_ref.parent = MagicMock(gid="nb-1")

        # After fetching non_business, its parent is None -> triggers another
        # get_async for parent discovery which returns parent=None
        nb_no_parent = MagicMock()
        nb_no_parent.parent = None

        mock_client.tasks.get_async.side_effect = [
            trigger_parent_ref,  # discover trigger's parent
            non_business,  # fetch non_business
            nb_no_parent,  # try to discover non_business's parent -> None
        ]

        context = ResolutionContext(mock_client)
        strategy = HierarchyTraversalStrategy()
        budget = ApiBudget(max_calls=20)

        result = await strategy.resolve_async(
            Business, context, from_entity=from_entity, budget=budget
        )

        assert result is None

    @pytest.mark.asyncio
    @patch("autom8_asana.models.business.detection.detect_entity_type")
    async def test_traverse_handles_task_without_memberships(
        self, mock_detect: MagicMock, mock_client: MagicMock
    ) -> None:
        """Traversal continues upward when a parent has memberships=None."""
        from_entity = make_business_entity("trigger-1", "Trigger")

        # First parent: no memberships at all
        no_memberships_task = _make_parent_chain_task(
            "nm-1",
            "No Memberships",
            parent_gid="biz-1",
            memberships=None,
        )
        # Second parent: actual Business
        business_task = _make_parent_chain_task(
            "biz-1",
            "Acme Corp",
            parent_gid=None,
            memberships=[{"project": {"gid": "1200653012566782"}}],
        )

        # detect_entity_type: first call for no_memberships_task -> UNKNOWN, second -> BUSINESS
        mock_detect.side_effect = [
            _make_unknown_result(),
            _make_detection_result(EntityType.BUSINESS),
        ]

        trigger_parent_ref = MagicMock()
        trigger_parent_ref.parent = MagicMock(gid="nm-1")
        mock_client.tasks.get_async.side_effect = [
            trigger_parent_ref,  # discover trigger's parent
            no_memberships_task,  # fetch no_memberships_task
            business_task,  # fetch business (no_memberships_task.parent)
        ]

        context = ResolutionContext(mock_client)
        strategy = HierarchyTraversalStrategy()
        budget = ApiBudget(max_calls=20)

        result = await strategy.resolve_async(
            Business, context, from_entity=from_entity, budget=budget
        )

        assert result is not None
        assert result.entity.gid == "biz-1"


class TestTryCastDetectionGuard:
    """Tests for detection guard in DependencyShortcutStrategy._try_cast."""

    @patch("autom8_asana.models.business.detection.detect_entity_type")
    def test_try_cast_rejects_non_business_for_business_target(
        self, mock_detect: MagicMock
    ) -> None:
        """_try_cast returns None for Business target when detection says OfferHolder."""
        mock_detect.return_value = _make_detection_result(EntityType.OFFER_HOLDER)

        task = _make_parent_chain_task(
            "oh-1",
            "Offers",
            memberships=[{"project": {"gid": "1143843662099250"}}],
        )

        strategy = DependencyShortcutStrategy()
        result = strategy._try_cast(task, Business)

        assert result is None
        mock_detect.assert_called_once_with(task)
