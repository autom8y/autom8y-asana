"""Tests for upward traversal in business model hydration.

Per TDD-HYDRATION Phase 2: Focused tests for parent chain navigation,
cycle detection, and max depth enforcement.

Per ADR-0068: Type detection during upward traversal.
Per ADR-0069: to_business_async() instance methods for upward navigation.
Per ADR-0070: Partial failure handling during upward traversal.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.errors import HydrationError
from autom8_asana.models.business.business import Business
from autom8_asana.models.business.contact import Contact, ContactHolder
from autom8_asana.models.business.hydration import (
    _traverse_upward_async,
)
from autom8_asana.models.business.offer import Offer, OfferHolder
from autom8_asana.models.business.process import ProcessHolder
from autom8_asana.models.business.unit import Unit, UnitHolder
from autom8_asana.models.common import NameGid
from autom8_asana.models.task import Task

# =============================================================================
# Parent Chain Navigation Tests
# =============================================================================


@pytest.mark.asyncio
class TestParentChainNavigation:
    """Tests for navigating parent chains during upward traversal."""

    async def test_navigate_contact_to_business_two_levels(self) -> None:
        """Navigate from Contact to Business (2 levels).

        Path: Contact -> ContactHolder -> Business
        """
        contact = Task(
            gid="c1",
            name="John Doe",
            parent=NameGid(gid="ch1", name="Contacts"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            if gid == "ch1":
                return Task(
                    gid="ch1",
                    name="Contacts",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                )
            elif gid == "b1":
                return Task(gid="b1", name="Acme Corp")
            raise ValueError(f"Unexpected gid: {gid}")

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            if gid == "b1":
                mock.collect = AsyncMock(
                    return_value=[
                        Task(gid="ch1", name="Contacts"),
                        Task(gid="uh1", name="Units"),
                    ]
                )
            else:
                mock.collect = AsyncMock(return_value=[])
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        business, path = await _traverse_upward_async(contact, client)

        assert isinstance(business, Business)
        assert business.gid == "b1"
        assert len(path) == 1
        assert isinstance(path[0], ContactHolder)
        assert path[0].gid == "ch1"

    async def test_navigate_offer_to_business_four_levels(self) -> None:
        """Navigate from Offer to Business (4 levels).

        Path: Offer -> OfferHolder -> Unit -> UnitHolder -> Business
        """
        offer = Task(
            gid="o1",
            name="Offer 1",
            parent=NameGid(gid="oh1", name="Offers"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            tasks = {
                "oh1": Task(
                    gid="oh1",
                    name="Offers",
                    parent=NameGid(gid="u1", name="Premium"),
                ),
                "u1": Task(
                    gid="u1",
                    name="Premium",
                    parent=NameGid(gid="uh1", name="Units"),
                ),
                "uh1": Task(
                    gid="uh1",
                    name="Units",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            if gid in tasks:
                return tasks[gid]
            raise ValueError(f"Unexpected gid: {gid}")

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            subtask_map = {
                "u1": [
                    Task(gid="oh1", name="Offers"),
                    Task(gid="ph1", name="Processes"),
                ],
                "b1": [
                    Task(gid="ch1", name="Contacts"),
                    Task(gid="uh1", name="Units"),
                ],
            }
            mock.collect = AsyncMock(return_value=subtask_map.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        business, path = await _traverse_upward_async(offer, client)

        assert isinstance(business, Business)
        assert business.gid == "b1"
        assert len(path) == 3
        assert isinstance(path[0], OfferHolder)
        assert path[0].gid == "oh1"
        assert isinstance(path[1], Unit)
        assert path[1].gid == "u1"
        assert isinstance(path[2], UnitHolder)
        assert path[2].gid == "uh1"

    async def test_navigate_process_to_business_four_levels(self) -> None:
        """Navigate from Process to Business (4 levels).

        Path: Process -> ProcessHolder -> Unit -> UnitHolder -> Business
        """
        process = Task(
            gid="p1",
            name="Build Process",
            parent=NameGid(gid="ph1", name="Processes"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            tasks = {
                "ph1": Task(
                    gid="ph1",
                    name="Processes",
                    parent=NameGid(gid="u1", name="Premium"),
                ),
                "u1": Task(
                    gid="u1",
                    name="Premium",
                    parent=NameGid(gid="uh1", name="Units"),
                ),
                "uh1": Task(
                    gid="uh1",
                    name="Units",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            subtask_map = {
                "u1": [
                    Task(gid="oh1", name="Offers"),
                    Task(gid="ph1", name="Processes"),
                ],
                "b1": [
                    Task(gid="ch1", name="Contacts"),
                    Task(gid="uh1", name="Units"),
                ],
            }
            mock.collect = AsyncMock(return_value=subtask_map.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        business, path = await _traverse_upward_async(process, client)

        assert isinstance(business, Business)
        assert len(path) == 3
        assert isinstance(path[0], ProcessHolder)
        assert isinstance(path[1], Unit)
        assert isinstance(path[2], UnitHolder)

    async def test_navigate_unit_to_business_two_levels(self) -> None:
        """Navigate from Unit to Business (2 levels).

        Path: Unit -> UnitHolder -> Business
        """
        unit = Task(
            gid="u1",
            name="Premium Package",
            parent=NameGid(gid="uh1", name="Units"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            tasks = {
                "uh1": Task(
                    gid="uh1",
                    name="Units",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            if gid == "b1":
                mock.collect = AsyncMock(
                    return_value=[
                        Task(gid="ch1", name="Contacts"),
                        Task(gid="uh1", name="Units"),
                    ]
                )
            else:
                mock.collect = AsyncMock(return_value=[])
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        business, path = await _traverse_upward_async(unit, client)

        assert isinstance(business, Business)
        assert business.gid == "b1"
        assert len(path) == 1
        assert isinstance(path[0], UnitHolder)


# =============================================================================
# Cycle Detection Tests
# =============================================================================


@pytest.mark.asyncio
class TestCycleDetection:
    """Tests for cycle detection in upward traversal."""

    async def test_direct_cycle_detected(self) -> None:
        """Detect direct cycle: task -> parent -> task."""
        task = Task(
            gid="t1",
            name="Task 1",
            parent=NameGid(gid="t2", name="Task 2"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            if gid == "t2":
                return Task(
                    gid="t2",
                    name="Task 2",
                    parent=NameGid(gid="t1", name="Task 1"),  # Cycle back
                )
            raise ValueError(f"Unexpected gid: {gid}")

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=[])
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        with pytest.raises(HydrationError) as exc_info:
            await _traverse_upward_async(task, client)

        error = exc_info.value
        assert error.phase == "upward"
        assert "Cycle detected" in str(error)
        assert "t1" in str(error)

    async def test_three_node_cycle_detected(self) -> None:
        """Detect 3-node cycle: t1 -> t2 -> t3 -> t1."""
        task = Task(
            gid="t1",
            name="Task 1",
            parent=NameGid(gid="t2", name="Task 2"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            tasks = {
                "t2": Task(
                    gid="t2",
                    name="Task 2",
                    parent=NameGid(gid="t3", name="Task 3"),
                ),
                "t3": Task(
                    gid="t3",
                    name="Task 3",
                    parent=NameGid(gid="t1", name="Task 1"),  # Cycle back
                ),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=[])
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        with pytest.raises(HydrationError) as exc_info:
            await _traverse_upward_async(task, client)

        error = exc_info.value
        assert error.phase == "upward"
        assert "Cycle detected" in str(error)

    async def test_self_referencing_parent_detected(self) -> None:
        """Detect self-reference: task -> task (parent points to self)."""
        task = Task(
            gid="t1",
            name="Task 1",
            parent=NameGid(gid="t1", name="Task 1"),  # Self-reference
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            # Should never be called - cycle detected on first parent check
            raise ValueError(f"Unexpected gid: {gid}")

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        with pytest.raises(HydrationError) as exc_info:
            await _traverse_upward_async(task, client)

        error = exc_info.value
        assert error.phase == "upward"
        assert "Cycle detected" in str(error)


# =============================================================================
# Max Depth Enforcement Tests
# =============================================================================


@pytest.mark.asyncio
class TestMaxDepthEnforcement:
    """Tests for max depth limits in upward traversal."""

    async def test_default_max_depth_is_ten(self) -> None:
        """Default max depth is 10 levels."""
        # Create a chain that exceeds 10 levels
        task = Task(
            gid="t0",
            name="Start",
            parent=NameGid(gid="t1", name="Level 1"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            level = int(gid[1:])
            return Task(
                gid=gid,
                name=f"Level {level}",
                parent=NameGid(gid=f"t{level + 1}", name=f"Level {level + 1}"),
            )

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=[])
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        with pytest.raises(HydrationError) as exc_info:
            await _traverse_upward_async(task, client)

        error = exc_info.value
        assert "Max traversal depth" in str(error)
        assert "(10)" in str(error)

    async def test_custom_max_depth(self) -> None:
        """Custom max depth can be specified."""
        task = Task(
            gid="t0",
            name="Start",
            parent=NameGid(gid="t1", name="Level 1"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            level = int(gid[1:])
            return Task(
                gid=gid,
                name=f"Level {level}",
                parent=NameGid(gid=f"t{level + 1}", name=f"Level {level + 1}"),
            )

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=[])
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        with pytest.raises(HydrationError) as exc_info:
            await _traverse_upward_async(task, client, max_depth=3)

        error = exc_info.value
        assert "Max traversal depth" in str(error)
        assert "(3)" in str(error)

    async def test_exactly_at_max_depth_succeeds(self) -> None:
        """Traversal succeeds when Business is at exactly max_depth."""
        # Chain: t0 -> t1 -> t2 -> b1 (Business)
        task = Task(
            gid="t0",
            name="Start",
            parent=NameGid(gid="t1", name="Level 1"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            tasks = {
                "t1": Task(
                    gid="t1",
                    name="Level 1",
                    parent=NameGid(gid="t2", name="Level 2"),
                ),
                "t2": Task(
                    gid="t2",
                    name="Level 2",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            if gid == "b1":
                mock.collect = AsyncMock(
                    return_value=[Task(gid="ch1", name="Contacts")]
                )
            else:
                mock.collect = AsyncMock(return_value=[])
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        # Should succeed with max_depth=3 (exactly 3 levels to Business)
        business, path = await _traverse_upward_async(task, client, max_depth=3)

        assert isinstance(business, Business)
        assert business.gid == "b1"


# =============================================================================
# Root Without Business Tests
# =============================================================================


@pytest.mark.asyncio
class TestRootWithoutBusiness:
    """Tests for reaching root without finding Business."""

    async def test_no_parent_raises_error(self) -> None:
        """Error when starting task has no parent."""
        task = Task(gid="orphan", name="Orphan Task", parent=None)
        client = MagicMock()

        with pytest.raises(HydrationError) as exc_info:
            await _traverse_upward_async(task, client)

        error = exc_info.value
        assert error.entity_gid == "orphan"
        assert error.phase == "upward"
        assert "Reached root without finding Business" in str(error)

    async def test_root_task_without_business_structure(self) -> None:
        """Error when reaching root task that is not a Business."""
        task = Task(
            gid="t1",
            name="Child",
            parent=NameGid(gid="root", name="Root Task"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            if gid == "root":
                return Task(gid="root", name="Root Task", parent=None)
            raise ValueError(f"Unexpected gid: {gid}")

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=[])  # No holder subtasks
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        with pytest.raises(HydrationError) as exc_info:
            await _traverse_upward_async(task, client)

        error = exc_info.value
        assert error.phase == "upward"
        assert "Reached root without finding Business" in str(error)


# =============================================================================
# Type Detection During Traversal Tests
# =============================================================================


@pytest.mark.asyncio
class TestTypeDetectionDuringTraversal:
    """Tests for entity type detection during upward traversal."""

    async def test_holder_detected_by_name(self) -> None:
        """Holder types detected by name (fast path)."""
        contact = Task(
            gid="c1",
            name="John",
            parent=NameGid(gid="ch1", name="Contacts"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            tasks = {
                "ch1": Task(
                    gid="ch1",
                    name="Contacts",  # Detected as CONTACT_HOLDER by name
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        call_count = 0

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            mock = AsyncMock()
            # Only Business detection needs subtasks
            if gid == "b1":
                mock.collect = AsyncMock(
                    return_value=[Task(gid="ch1", name="Contacts")]
                )
            else:
                mock.collect = AsyncMock(return_value=[])
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        business, path = await _traverse_upward_async(contact, client)

        # Should not call subtasks_async for ContactHolder (detected by name)
        # Only called for Business type detection
        assert isinstance(path[0], ContactHolder)

    async def test_business_detected_by_structure(self) -> None:
        """Business detected by structure when name is arbitrary."""
        unit = Task(
            gid="u1",
            name="Premium",
            parent=NameGid(gid="uh1", name="Units"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            tasks = {
                "uh1": Task(
                    gid="uh1",
                    name="Units",
                    parent=NameGid(gid="b1", name="Custom Business Name"),
                ),
                "b1": Task(gid="b1", name="Custom Business Name"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            if gid == "b1":
                # Business detected by having holder subtasks
                mock.collect = AsyncMock(
                    return_value=[
                        Task(gid="ch1", name="Contacts"),
                        Task(gid="uh1", name="Units"),
                        Task(gid="lh1", name="Location"),
                    ]
                )
            else:
                mock.collect = AsyncMock(return_value=[])
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        business, path = await _traverse_upward_async(unit, client)

        assert isinstance(business, Business)
        assert business.name == "Custom Business Name"


# =============================================================================
# Entity to_business_async Tests
# =============================================================================


@pytest.mark.asyncio
class TestEntityToBusinessAsync:
    """Tests for to_business_async() instance methods."""

    async def test_contact_to_business_async_with_full_hydration(self) -> None:
        """Contact.to_business_async() returns fully hydrated Business."""
        contact = Contact(
            gid="c1",
            name="John Doe",
            parent=NameGid(gid="ch1", name="Contacts"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            tasks = {
                "ch1": Task(
                    gid="ch1",
                    name="Contacts",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        mock_responses = {
            "b1": [Task(gid="ch1", name="Contacts")],
            "ch1": [Task(gid="c1", name="John Doe")],
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        business = await contact.to_business_async(client)

        assert isinstance(business, Business)
        assert business.gid == "b1"
        assert business._contact_holder is not None
        assert len(business.contacts) == 1

    async def test_offer_to_business_async_with_full_hydration(self) -> None:
        """Offer.to_business_async() returns fully hydrated Business."""
        offer = Offer(
            gid="o1",
            name="Offer 1",
            parent=NameGid(gid="oh1", name="Offers"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            tasks = {
                "oh1": Task(
                    gid="oh1",
                    name="Offers",
                    parent=NameGid(gid="u1", name="Premium"),
                ),
                "u1": Task(
                    gid="u1",
                    name="Premium",
                    parent=NameGid(gid="uh1", name="Units"),
                ),
                "uh1": Task(
                    gid="uh1",
                    name="Units",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        mock_responses = {
            "u1": [Task(gid="oh1", name="Offers"), Task(gid="ph1", name="Processes")],
            "b1": [Task(gid="uh1", name="Units")],
            "uh1": [Task(gid="u1", name="Premium")],
            "oh1": [Task(gid="o1", name="Offer 1")],
            "ph1": [],
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        business = await offer.to_business_async(client)

        assert isinstance(business, Business)
        assert len(business.units) == 1
        assert len(business.units[0].offers) == 1

    async def test_unit_to_business_async_with_full_hydration(self) -> None:
        """Unit.to_business_async() returns fully hydrated Business."""
        unit = Unit(
            gid="u1",
            name="Premium Package",
            parent=NameGid(gid="uh1", name="Units"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            tasks = {
                "uh1": Task(
                    gid="uh1",
                    name="Units",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        mock_responses = {
            "b1": [Task(gid="uh1", name="Units")],
            "uh1": [Task(gid="u1", name="Premium Package")],
            "u1": [Task(gid="oh1", name="Offers")],
            "oh1": [],
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        business = await unit.to_business_async(client)

        assert isinstance(business, Business)
        assert len(business.units) == 1

    async def test_to_business_async_without_hydration(self) -> None:
        """to_business_async(hydrate_full=False) skips full hydration."""
        contact = Contact(
            gid="c1",
            name="John Doe",
            parent=NameGid(gid="ch1", name="Contacts"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            tasks = {
                "ch1": Task(
                    gid="ch1",
                    name="Contacts",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            if gid == "b1":
                mock.collect = AsyncMock(
                    return_value=[Task(gid="ch1", name="Contacts")]
                )
            else:
                mock.collect = AsyncMock(return_value=[])
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        business = await contact.to_business_async(client, hydrate_full=False)

        assert isinstance(business, Business)
        assert business.gid == "b1"
        # Holders not populated because hydration was skipped
        assert business._contact_holder is None

    async def test_to_business_async_with_partial_ok(self) -> None:
        """to_business_async(partial_ok=True) continues on hydration failure."""
        contact = Contact(
            gid="c1",
            name="John Doe",
            parent=NameGid(gid="ch1", name="Contacts"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            tasks = {
                "ch1": Task(
                    gid="ch1",
                    name="Contacts",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        call_count = 0

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            mock = AsyncMock()
            if call_count == 1:
                mock.collect = AsyncMock(
                    return_value=[Task(gid="ch1", name="Contacts")]
                )
            else:
                mock.collect = AsyncMock(side_effect=RuntimeError("API error"))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        # Should not raise with partial_ok=True
        business = await contact.to_business_async(client, partial_ok=True)
        assert business.gid == "b1"


# =============================================================================
# Reference Update Tests
# =============================================================================


@pytest.mark.asyncio
class TestReferenceUpdates:
    """Tests for reference updates after to_business_async()."""

    async def test_contact_references_updated(self) -> None:
        """Contact references updated after to_business_async()."""
        contact = Contact(
            gid="c1",
            name="John Doe",
            parent=NameGid(gid="ch1", name="Contacts"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            tasks = {
                "ch1": Task(
                    gid="ch1",
                    name="Contacts",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        mock_responses = {
            "b1": [Task(gid="ch1", name="Contacts")],
            "ch1": [Task(gid="c1", name="John Doe")],
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        business = await contact.to_business_async(client)

        assert contact._business is business
        assert contact._contact_holder is business._contact_holder

    async def test_offer_references_updated(self) -> None:
        """Offer references updated after to_business_async()."""
        offer = Offer(
            gid="o1",
            name="Offer 1",
            parent=NameGid(gid="oh1", name="Offers"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            tasks = {
                "oh1": Task(
                    gid="oh1",
                    name="Offers",
                    parent=NameGid(gid="u1", name="Premium"),
                ),
                "u1": Task(
                    gid="u1",
                    name="Premium",
                    parent=NameGid(gid="uh1", name="Units"),
                ),
                "uh1": Task(
                    gid="uh1",
                    name="Units",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        mock_responses = {
            "u1": [Task(gid="oh1", name="Offers"), Task(gid="ph1", name="Processes")],
            "b1": [Task(gid="uh1", name="Units")],
            "uh1": [Task(gid="u1", name="Premium")],
            "oh1": [Task(gid="o1", name="Offer 1")],
            "ph1": [],
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        business = await offer.to_business_async(client)

        assert offer._business is business
        assert offer._unit is not None
        assert offer._unit.gid == "u1"
        assert offer._offer_holder is not None

    async def test_unit_references_updated(self) -> None:
        """Unit references updated after to_business_async()."""
        unit = Unit(
            gid="u1",
            name="Premium Package",
            parent=NameGid(gid="uh1", name="Units"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            tasks = {
                "uh1": Task(
                    gid="uh1",
                    name="Units",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        mock_responses = {
            "b1": [Task(gid="uh1", name="Units")],
            "uh1": [Task(gid="u1", name="Premium Package")],
            "u1": [Task(gid="oh1", name="Offers")],
            "oh1": [],
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        business = await unit.to_business_async(client)

        assert unit._business is business
        assert unit._unit_holder is business._unit_holder
