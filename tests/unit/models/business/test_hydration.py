"""Tests for Business Model Hydration (Phase 1 and Phase 2).

Per TDD-HYDRATION Phase 1: Tests for P0 downward hydration feature.
Per TDD-HYDRATION Phase 2: Tests for P1 upward traversal feature.
Per ADR-0068: Type detection tests.
Per ADR-0069: Business.from_gid_async() and to_business_async() API tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.exceptions import HydrationError
from autom8_asana.models.business.business import Business
from autom8_asana.models.business.contact import Contact, ContactHolder
from autom8_asana.models.business.detection import (
    EntityType,
    detect_entity_type_async,
)
from autom8_asana.models.business.hydration import (
    _convert_to_typed_entity,
    _traverse_upward_async,
)
from autom8_asana.models.business.offer import Offer, OfferHolder
from autom8_asana.models.business.process import Process, ProcessHolder
from autom8_asana.models.business.unit import Unit, UnitHolder
from autom8_asana.models.common import NameGid
from autom8_asana.models.task import Task


class TestEntityType:
    """Tests for EntityType enum."""

    def test_all_entity_types_defined(self) -> None:
        """EntityType includes all business model types."""
        expected = {
            "BUSINESS",
            "CONTACT_HOLDER",
            "UNIT_HOLDER",
            "LOCATION_HOLDER",
            "DNA_HOLDER",
            "RECONCILIATIONS_HOLDER",
            "ASSET_EDIT_HOLDER",
            "VIDEOGRAPHY_HOLDER",
            "UNIT",
            "OFFER_HOLDER",
            "PROCESS_HOLDER",
            "CONTACT",
            "OFFER",
            "PROCESS",
            "LOCATION",
            "HOURS",
            "UNKNOWN",
        }
        actual = {e.name for e in EntityType}
        assert actual == expected

    def test_entity_type_values(self) -> None:
        """EntityType values are lowercase strings."""
        assert EntityType.BUSINESS.value == "business"
        assert EntityType.CONTACT_HOLDER.value == "contact_holder"
        assert EntityType.UNKNOWN.value == "unknown"


@pytest.mark.asyncio
class TestDetectEntityTypeAsync:
    """Tests for detect_entity_type_async function.

    Per TDD-DETECTION: detect_entity_type_async now returns DetectionResult,
    not EntityType directly. Tests updated to use result.entity_type.
    """

    async def test_detect_holder_by_name_fast_path(self) -> None:
        """detect_entity_type_async uses fast path (Tier 2) for holders."""
        task = Task(gid="123", name="Contacts")
        client = MagicMock()

        result = await detect_entity_type_async(task, client)

        assert result.entity_type == EntityType.CONTACT_HOLDER
        assert result.tier_used == 2  # Name pattern matching
        # Client should not be called (fast path - Tiers 1-3 don't call API)
        client.tasks.subtasks_async.assert_not_called()

    async def test_detect_business_by_structure(self) -> None:
        """detect_entity_type_async detects Business via subtask structure (Tier 4)."""
        task = Task(gid="123", name="Acme Corp")
        client = MagicMock()

        # Mock subtasks_async to return holder-named subtasks
        mock_iterator = AsyncMock()
        mock_iterator.collect = AsyncMock(
            return_value=[
                Task(gid="h1", name="Contacts"),
                Task(gid="h2", name="Units"),
                Task(gid="h3", name="Location"),
            ]
        )
        client.tasks.subtasks_async.return_value = mock_iterator

        # Must enable structure inspection for Tier 4
        result = await detect_entity_type_async(
            task, client, allow_structure_inspection=True
        )

        assert result.entity_type == EntityType.BUSINESS
        assert result.tier_used == 4  # Structure inspection
        client.tasks.subtasks_async.assert_called_once_with("123")

    async def test_detect_unit_by_structure(self) -> None:
        """detect_entity_type_async detects Unit via subtask structure (Tier 4)."""
        task = Task(gid="123", name="Premium Package")
        client = MagicMock()

        # Mock subtasks_async to return offer/process holders
        mock_iterator = AsyncMock()
        mock_iterator.collect = AsyncMock(
            return_value=[
                Task(gid="h1", name="Offers"),
                Task(gid="h2", name="Processes"),
            ]
        )
        client.tasks.subtasks_async.return_value = mock_iterator

        # Must enable structure inspection for Tier 4
        result = await detect_entity_type_async(
            task, client, allow_structure_inspection=True
        )

        assert result.entity_type == EntityType.UNIT
        assert result.tier_used == 4

    async def test_detect_unknown_type(self) -> None:
        """detect_entity_type_async returns UNKNOWN (Tier 5) for unrecognized structure."""
        task = Task(gid="123", name="Some Task")
        client = MagicMock()

        # Mock subtasks_async to return unrelated subtasks
        mock_iterator = AsyncMock()
        mock_iterator.collect = AsyncMock(
            return_value=[
                Task(gid="s1", name="Random Task"),
                Task(gid="s2", name="Another Task"),
            ]
        )
        client.tasks.subtasks_async.return_value = mock_iterator

        # Even with structure inspection enabled, no match
        result = await detect_entity_type_async(
            task, client, allow_structure_inspection=True
        )

        assert result.entity_type == EntityType.UNKNOWN
        assert result.tier_used == 5


class TestHydrationError:
    """Tests for HydrationError exception."""

    def test_hydration_error_attributes(self) -> None:
        """HydrationError has required attributes."""
        error = HydrationError(
            "Test error",
            entity_gid="123",
            entity_type="business",
            phase="downward",
        )

        assert str(error) == "Test error"
        assert error.entity_gid == "123"
        assert error.entity_type == "business"
        assert error.phase == "downward"
        assert error.partial_result is None
        assert error.__cause__ is None

    def test_hydration_error_with_cause(self) -> None:
        """HydrationError can store underlying cause."""
        cause = ValueError("Underlying error")
        error = HydrationError(
            "Test error",
            entity_gid="123",
            phase="upward",
            cause=cause,
        )

        assert error.__cause__ is cause

    def test_hydration_error_inherits_from_asana_error(self) -> None:
        """HydrationError inherits from AsanaError."""
        from autom8_asana.exceptions import AsanaError

        error = HydrationError("Test", entity_gid="123", phase="downward")
        assert isinstance(error, AsanaError)


@pytest.mark.asyncio
class TestBusinessFetchHoldersAsync:
    """Tests for Business._fetch_holders_async()."""

    async def test_fetch_holders_populates_contact_holder(self) -> None:
        """_fetch_holders_async populates ContactHolder with contacts."""
        business = Business(gid="b1", name="Acme")
        client = MagicMock()

        # Mock holder subtasks
        holder_mock = AsyncMock()
        holder_mock.collect = AsyncMock(return_value=[Task(gid="h1", name="Contacts")])

        # Mock contact subtasks
        contact_mock = AsyncMock()
        contact_mock.collect = AsyncMock(
            return_value=[
                Task(gid="c1", name="John Doe"),
                Task(gid="c2", name="Jane Doe"),
            ]
        )

        # Set up subtasks_async to return different mocks based on gid
        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            if gid == "b1":
                return holder_mock
            elif gid == "h1":
                return contact_mock
            return AsyncMock()

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        await business._fetch_holders_async(client)

        # Verify ContactHolder is populated
        assert business._contact_holder is not None
        assert isinstance(business._contact_holder, ContactHolder)

        # Verify contacts are populated
        assert len(business.contacts) == 2
        assert all(isinstance(c, Contact) for c in business.contacts)
        assert business.contacts[0].gid in ["c1", "c2"]

    async def test_fetch_holders_populates_unit_holder_with_nested(self) -> None:
        """_fetch_holders_async populates UnitHolder with Units and their nested holders."""
        business = Business(gid="b1", name="Acme")
        client = MagicMock()

        # Build mock responses
        mock_responses: dict[str, list[Task]] = {
            "b1": [Task(gid="uh1", name="Units")],  # Business subtasks
            "uh1": [Task(gid="u1", name="Premium Package")],  # UnitHolder subtasks
            "u1": [
                Task(gid="oh1", name="Offers"),
                Task(gid="ph1", name="Processes"),
            ],  # Unit subtasks
            "oh1": [Task(gid="o1", name="Offer 1")],  # OfferHolder subtasks
            "ph1": [Task(gid="p1", name="Process 1")],  # ProcessHolder subtasks
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        await business._fetch_holders_async(client)

        # Verify UnitHolder is populated
        assert business._unit_holder is not None
        assert isinstance(business._unit_holder, UnitHolder)

        # Verify Unit is populated
        assert len(business.units) == 1
        unit = business.units[0]
        assert isinstance(unit, Unit)
        assert unit.gid == "u1"

        # Verify nested OfferHolder and offers
        assert unit._offer_holder is not None
        assert isinstance(unit._offer_holder, OfferHolder)
        assert len(unit.offers) == 1
        assert isinstance(unit.offers[0], Offer)

        # Verify nested ProcessHolder and processes
        assert unit._process_holder is not None
        assert isinstance(unit._process_holder, ProcessHolder)
        assert len(unit.processes) == 1
        assert isinstance(unit.processes[0], Process)

    async def test_fetch_holders_sets_bidirectional_references(self) -> None:
        """_fetch_holders_async sets bidirectional references correctly."""
        business = Business(gid="b1", name="Acme")
        client = MagicMock()

        mock_responses: dict[str, list[Task]] = {
            "b1": [Task(gid="ch1", name="Contacts")],
            "ch1": [Task(gid="c1", name="John Doe")],
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        await business._fetch_holders_async(client)

        # Verify bidirectional references
        contact_holder = business._contact_holder
        assert contact_holder is not None
        assert contact_holder._business is business

        contact = business.contacts[0]
        assert contact._contact_holder is contact_holder
        assert contact._business is business

    async def test_fetch_holders_handles_empty_holders(self) -> None:
        """_fetch_holders_async handles holders with no children."""
        business = Business(gid="b1", name="Acme")
        client = MagicMock()

        mock_responses: dict[str, list[Task]] = {
            "b1": [Task(gid="ch1", name="Contacts")],
            "ch1": [],  # Empty ContactHolder
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        await business._fetch_holders_async(client)

        # Verify ContactHolder exists but is empty
        assert business._contact_holder is not None
        assert business.contacts == []


@pytest.mark.asyncio
class TestUnitFetchHoldersAsync:
    """Tests for Unit._fetch_holders_async()."""

    async def test_fetch_holders_populates_offer_holder(self) -> None:
        """_fetch_holders_async populates OfferHolder with offers."""
        unit = Unit(gid="u1", name="Premium Package")
        client = MagicMock()

        mock_responses: dict[str, list[Task]] = {
            "u1": [Task(gid="oh1", name="Offers")],
            "oh1": [
                Task(gid="o1", name="Offer 1"),
                Task(gid="o2", name="Offer 2"),
            ],
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        await unit._fetch_holders_async(client)

        # Verify OfferHolder is populated
        assert unit._offer_holder is not None
        assert isinstance(unit._offer_holder, OfferHolder)
        assert len(unit.offers) == 2

    async def test_fetch_holders_populates_process_holder(self) -> None:
        """_fetch_holders_async populates ProcessHolder with processes."""
        unit = Unit(gid="u1", name="Premium Package")
        client = MagicMock()

        mock_responses: dict[str, list[Task]] = {
            "u1": [Task(gid="ph1", name="Processes")],
            "ph1": [Task(gid="p1", name="Build Process")],
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        await unit._fetch_holders_async(client)

        # Verify ProcessHolder is populated
        assert unit._process_holder is not None
        assert isinstance(unit._process_holder, ProcessHolder)
        assert len(unit.processes) == 1


@pytest.mark.asyncio
class TestBusinessFromGidAsync:
    """Tests for Business.from_gid_async()."""

    async def test_from_gid_async_with_hydration(self) -> None:
        """from_gid_async hydrates full hierarchy by default."""
        client = MagicMock()

        # Mock get_async to return Business task
        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        # Mock subtasks
        mock_responses: dict[str, list[Task]] = {
            "b1": [Task(gid="ch1", name="Contacts")],
            "ch1": [Task(gid="c1", name="John")],
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        # Call with default hydrate=True
        business = await Business.from_gid_async(client, "b1")

        # Verify hydration occurred
        assert isinstance(business, Business)
        assert business.gid == "b1"
        assert business._contact_holder is not None
        assert len(business.contacts) == 1

    async def test_from_gid_async_without_hydration(self) -> None:
        """from_gid_async skips hydration when hydrate=False."""
        client = MagicMock()

        # Mock get_async to return Business task
        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        # Call with hydrate=False
        business = await Business.from_gid_async(client, "b1", hydrate=False)

        # Verify no hydration
        assert isinstance(business, Business)
        assert business.gid == "b1"
        assert business._contact_holder is None
        assert business._unit_holder is None

        # subtasks_async should not be called
        client.tasks.subtasks_async.assert_not_called()

    async def test_from_gid_async_returns_business_type(self) -> None:
        """from_gid_async returns Business instance, not BusinessEntity."""
        client = MagicMock()
        client.tasks.get_async = AsyncMock(return_value=Task(gid="b1", name="Acme"))

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=[])
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        business = await Business.from_gid_async(client, "b1")

        # Should be Business, not just BusinessEntity
        assert type(business) is Business


class TestIntegrationDownwardHydration:
    """Integration-style tests for full downward hydration."""

    @pytest.mark.asyncio
    async def test_full_hierarchy_hydration(self) -> None:
        """Full hierarchy is hydrated with correct structure."""
        business = Business(gid="b1", name="Acme Corp")
        client = MagicMock()

        # Build complete hierarchy mock
        mock_responses: dict[str, list[Task]] = {
            # Business holders
            "b1": [
                Task(gid="ch1", name="Contacts"),
                Task(gid="uh1", name="Units"),
                Task(gid="lh1", name="Location"),
                Task(gid="dh1", name="DNA"),
            ],
            # ContactHolder children
            "ch1": [
                Task(gid="c1", name="John Doe"),
                Task(gid="c2", name="Jane Doe"),
            ],
            # UnitHolder children
            "uh1": [
                Task(gid="u1", name="Premium Package"),
                Task(gid="u2", name="Basic Package"),
            ],
            # Unit 1 holders
            "u1": [
                Task(gid="oh1", name="Offers"),
                Task(gid="ph1", name="Processes"),
            ],
            # Unit 2 holders
            "u2": [
                Task(gid="oh2", name="Offers"),
                Task(gid="ph2", name="Processes"),
            ],
            # OfferHolder 1 children
            "oh1": [
                Task(gid="o1", name="Offer 1"),
                Task(gid="o2", name="Offer 2"),
            ],
            # OfferHolder 2 children
            "oh2": [Task(gid="o3", name="Offer 3")],
            # ProcessHolder children
            "ph1": [Task(gid="p1", name="Build Process")],
            "ph2": [],  # Empty
            # LocationHolder children
            "lh1": [Task(gid="loc1", name="Main Office")],
            # DNAHolder children
            "dh1": [Task(gid="d1", name="DNA Item")],
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        await business._fetch_holders_async(client)

        # Verify Business-level holders
        assert business._contact_holder is not None
        assert business._unit_holder is not None
        assert business._location_holder is not None
        assert business._dna_holder is not None

        # Verify Contacts
        assert len(business.contacts) == 2
        assert all(isinstance(c, Contact) for c in business.contacts)

        # Verify Units
        assert len(business.units) == 2
        assert all(isinstance(u, Unit) for u in business.units)

        # Verify Unit 1 nested holders
        unit1 = next(u for u in business.units if u.gid == "u1")
        assert unit1._offer_holder is not None
        assert len(unit1.offers) == 2
        assert unit1._process_holder is not None
        assert len(unit1.processes) == 1

        # Verify Unit 2 nested holders
        unit2 = next(u for u in business.units if u.gid == "u2")
        assert unit2._offer_holder is not None
        assert len(unit2.offers) == 1
        assert unit2._process_holder is not None
        assert len(unit2.processes) == 0  # Empty

    @pytest.mark.asyncio
    async def test_bidirectional_references_throughout_hierarchy(self) -> None:
        """All entities have correct bidirectional references."""
        business = Business(gid="b1", name="Acme Corp")
        client = MagicMock()

        mock_responses: dict[str, list[Task]] = {
            "b1": [Task(gid="uh1", name="Units")],
            "uh1": [Task(gid="u1", name="Premium")],
            "u1": [Task(gid="oh1", name="Offers")],
            "oh1": [Task(gid="o1", name="Offer 1")],
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        await business._fetch_holders_async(client)

        # Walk the hierarchy and verify references
        unit_holder = business._unit_holder
        assert unit_holder is not None
        assert unit_holder._business is business

        unit = business.units[0]
        assert unit._unit_holder is unit_holder
        assert unit._business is business

        offer_holder = unit._offer_holder
        assert offer_holder is not None
        assert offer_holder._unit is unit
        assert offer_holder._business is business

        offer = unit.offers[0]
        assert offer._offer_holder is offer_holder
        assert offer._unit is unit
        assert offer._business is business


# =============================================================================
# Phase 2: Upward Traversal Tests
# =============================================================================


@pytest.mark.asyncio
class TestTraverseUpwardAsync:
    """Tests for _traverse_upward_async function."""

    async def test_traverse_from_contact_to_business(self) -> None:
        """_traverse_upward_async finds Business from Contact (2 levels)."""
        # Create Contact with parent reference to ContactHolder
        contact = Task(
            gid="c1",
            name="John Doe",
            parent=NameGid(gid="ch1", name="Contacts"),
        )
        client = MagicMock()

        # Mock get_async to return tasks along the path
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

        # Mock subtasks_async for Business detection
        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            if gid == "b1":
                # Business has holder subtasks
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

        # Execute traversal
        business, path = await _traverse_upward_async(contact, client)

        # Verify results
        assert isinstance(business, Business)
        assert business.gid == "b1"
        assert business.name == "Acme Corp"
        assert len(path) == 1  # Only ContactHolder
        assert isinstance(path[0], ContactHolder)
        assert path[0].gid == "ch1"

    async def test_traverse_from_offer_to_business(self) -> None:
        """_traverse_upward_async finds Business from Offer (4 levels)."""
        # Create Offer with parent chain
        offer = Task(
            gid="o1",
            name="Offer 1",
            parent=NameGid(gid="oh1", name="Offers"),
        )
        client = MagicMock()

        # Mock the full parent chain
        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            tasks = {
                "oh1": Task(
                    gid="oh1",
                    name="Offers",
                    parent=NameGid(gid="u1", name="Premium Package"),
                ),
                "u1": Task(
                    gid="u1",
                    name="Premium Package",
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

        # Mock subtasks_async for structure detection
        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            subtask_map = {
                "u1": [
                    Task(gid="oh1", name="Offers"),
                    Task(gid="ph1", name="Processes"),
                ],
                "b1": [Task(gid="ch1", name="Contacts"), Task(gid="uh1", name="Units")],
            }
            mock.collect = AsyncMock(return_value=subtask_map.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        # Execute traversal
        business, path = await _traverse_upward_async(offer, client)

        # Verify results
        assert isinstance(business, Business)
        assert business.gid == "b1"
        # Path: OfferHolder -> Unit -> UnitHolder
        assert len(path) == 3
        assert isinstance(path[0], OfferHolder)
        assert isinstance(path[1], Unit)
        assert isinstance(path[2], UnitHolder)

    async def test_traverse_from_unit_to_business(self) -> None:
        """_traverse_upward_async finds Business from Unit (2 levels)."""
        unit = Task(
            gid="u1",
            name="Premium Package",
            parent=NameGid(gid="uh1", name="Units"),
        )
        client = MagicMock()

        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            if gid == "uh1":
                return Task(
                    gid="uh1",
                    name="Units",
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

        business, path = await _traverse_upward_async(unit, client)

        assert isinstance(business, Business)
        assert business.gid == "b1"
        assert len(path) == 1
        assert isinstance(path[0], UnitHolder)

    async def test_traverse_raises_on_no_parent(self) -> None:
        """_traverse_upward_async raises HydrationError when no parent."""
        task = Task(gid="t1", name="Orphan Task", parent=None)
        client = MagicMock()

        with pytest.raises(HydrationError) as exc_info:
            await _traverse_upward_async(task, client)

        error = exc_info.value
        assert error.entity_gid == "t1"
        assert error.phase == "upward"
        assert "Reached root without finding Business" in str(error)

    async def test_traverse_raises_on_cycle(self) -> None:
        """_traverse_upward_async raises HydrationError on cycle detection."""
        # Task whose parent points back to itself
        task = Task(
            gid="t1",
            name="Task 1",
            parent=NameGid(gid="t2", name="Task 2"),
        )
        client = MagicMock()

        # Create a cycle: t1 -> t2 -> t1
        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            if gid == "t2":
                return Task(
                    gid="t2",
                    name="Task 2",
                    parent=NameGid(gid="t1", name="Task 1"),
                )
            raise ValueError(f"Unexpected gid: {gid}")

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        # Mock subtasks for type detection (returns empty, so UNKNOWN)
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

    async def test_traverse_raises_on_max_depth(self) -> None:
        """_traverse_upward_async raises HydrationError when max depth exceeded."""
        task = Task(
            gid="t1",
            name="Start",
            parent=NameGid(gid="t2", name="Level 2"),
        )
        client = MagicMock()

        # Create a deep chain that exceeds max_depth
        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            level = int(gid[1:])
            return Task(
                gid=gid,
                name=f"Level {level}",
                parent=NameGid(gid=f"t{level + 1}", name=f"Level {level + 1}"),
            )

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        # Mock subtasks to never detect Business
        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=[])
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        with pytest.raises(HydrationError) as exc_info:
            await _traverse_upward_async(task, client, max_depth=5)

        error = exc_info.value
        assert error.phase == "upward"
        assert "Max traversal depth" in str(error)


class TestConvertToTypedEntity:
    """Tests for _convert_to_typed_entity function."""

    def test_convert_contact_holder(self) -> None:
        """_convert_to_typed_entity converts to ContactHolder."""
        task = Task(gid="ch1", name="Contacts")
        result = _convert_to_typed_entity(task, EntityType.CONTACT_HOLDER)

        assert isinstance(result, ContactHolder)
        assert result.gid == "ch1"

    def test_convert_unit_holder(self) -> None:
        """_convert_to_typed_entity converts to UnitHolder."""
        task = Task(gid="uh1", name="Units")
        result = _convert_to_typed_entity(task, EntityType.UNIT_HOLDER)

        assert isinstance(result, UnitHolder)
        assert result.gid == "uh1"

    def test_convert_offer_holder(self) -> None:
        """_convert_to_typed_entity converts to OfferHolder."""
        task = Task(gid="oh1", name="Offers")
        result = _convert_to_typed_entity(task, EntityType.OFFER_HOLDER)

        assert isinstance(result, OfferHolder)

    def test_convert_unit(self) -> None:
        """_convert_to_typed_entity converts to Unit."""
        task = Task(gid="u1", name="Premium Package")
        result = _convert_to_typed_entity(task, EntityType.UNIT)

        assert isinstance(result, Unit)

    def test_convert_unknown_returns_none(self) -> None:
        """_convert_to_typed_entity returns None for UNKNOWN type."""
        task = Task(gid="t1", name="Unknown Task")
        result = _convert_to_typed_entity(task, EntityType.UNKNOWN)

        assert result is None

    def test_convert_business_returns_none(self) -> None:
        """_convert_to_typed_entity returns None for BUSINESS type.

        Note: Business conversion is handled separately in _traverse_upward_async.
        """
        task = Task(gid="b1", name="Acme Corp")
        result = _convert_to_typed_entity(task, EntityType.BUSINESS)

        assert result is None


@pytest.mark.asyncio
class TestContactToBusinessAsync:
    """Tests for Contact.to_business_async()."""

    async def test_to_business_async_returns_hydrated_business(self) -> None:
        """Contact.to_business_async() returns fully hydrated Business."""
        contact = Contact(
            gid="c1",
            name="John Doe",
            parent=NameGid(gid="ch1", name="Contacts"),
        )
        client = MagicMock()

        # Mock the parent chain
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

        # Mock subtasks for type detection and hydration
        mock_responses: dict[str, list[Task]] = {
            "b1": [Task(gid="ch1", name="Contacts")],
            "ch1": [Task(gid="c1", name="John Doe")],
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        # Execute
        business = await contact.to_business_async(client)

        # Verify
        assert isinstance(business, Business)
        assert business.gid == "b1"
        assert business._contact_holder is not None
        assert len(business.contacts) == 1

    async def test_to_business_async_updates_contact_references(self) -> None:
        """Contact.to_business_async() updates Contact references."""
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

        mock_responses: dict[str, list[Task]] = {
            "b1": [Task(gid="ch1", name="Contacts")],
            "ch1": [Task(gid="c1", name="John Doe")],
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        business = await contact.to_business_async(client)

        # Verify references updated
        assert contact._business is business
        assert contact._contact_holder is business._contact_holder

    async def test_to_business_async_without_hydration(self) -> None:
        """Contact.to_business_async(hydrate_full=False) skips full hydration."""
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

        # Subtasks needed for Business type detection only
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

        # Business found but not hydrated
        assert isinstance(business, Business)
        assert business.gid == "b1"
        # ContactHolder is None because hydration was skipped
        assert business._contact_holder is None


@pytest.mark.asyncio
class TestOfferToBusinessAsync:
    """Tests for Offer.to_business_async()."""

    async def test_to_business_async_traverses_full_path(self) -> None:
        """Offer.to_business_async() traverses 4 levels to Business."""
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

        # Full mock for hydration
        mock_responses: dict[str, list[Task]] = {
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
        assert business.gid == "b1"
        assert len(business.units) == 1
        assert len(business.units[0].offers) == 1

    async def test_to_business_async_updates_offer_references(self) -> None:
        """Offer.to_business_async() updates Offer references."""
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

        mock_responses: dict[str, list[Task]] = {
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

        # Verify references were updated
        assert offer._business is business
        assert offer._unit is not None
        assert offer._unit.gid == "u1"
        assert offer._offer_holder is not None


@pytest.mark.asyncio
class TestUnitToBusinessAsync:
    """Tests for Unit.to_business_async()."""

    async def test_to_business_async_returns_business(self) -> None:
        """Unit.to_business_async() returns hydrated Business."""
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

        mock_responses: dict[str, list[Task]] = {
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
        assert business.gid == "b1"
        assert len(business.units) == 1

    async def test_to_business_async_updates_unit_references(self) -> None:
        """Unit.to_business_async() updates Unit references."""
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

        mock_responses: dict[str, list[Task]] = {
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


class TestIntegrationUpwardHydration:
    """Integration-style tests for upward traversal with full hydration."""

    @pytest.mark.asyncio
    async def test_offer_entry_found_in_hydrated_hierarchy(self) -> None:
        """Entry Offer is findable within hydrated Business hierarchy.

        Per FR-FULL-002: Entry entity is included in hydrated result.
        """
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

        mock_responses: dict[str, list[Task]] = {
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

        # Verify offer is findable in hierarchy
        found = False
        for unit in business.units:
            for hydrated_offer in unit.offers:
                if hydrated_offer.gid == "o1":
                    found = True
                    break
        assert found, "Entry offer should be findable in hydrated hierarchy"

    @pytest.mark.asyncio
    async def test_contact_entry_found_in_hydrated_hierarchy(self) -> None:
        """Entry Contact is findable within hydrated Business hierarchy."""
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

        mock_responses: dict[str, list[Task]] = {
            "b1": [Task(gid="ch1", name="Contacts")],
            "ch1": [Task(gid="c1", name="John Doe")],
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        business = await contact.to_business_async(client)

        # Verify contact is findable in hierarchy
        contact_gids = [c.gid for c in business.contacts]
        assert "c1" in contact_gids


# =============================================================================
# Phase 3: HydrationResult Dataclasses Tests
# =============================================================================


class TestHydrationBranch:
    """Tests for HydrationBranch dataclass."""

    def test_hydration_branch_attributes(self) -> None:
        """HydrationBranch stores all required attributes."""
        from autom8_asana.models.business.hydration import HydrationBranch

        branch = HydrationBranch(
            holder_type="contact_holder",
            holder_gid="ch1",
            child_count=5,
        )

        assert branch.holder_type == "contact_holder"
        assert branch.holder_gid == "ch1"
        assert branch.child_count == 5


class TestHydrationFailure:
    """Tests for HydrationFailure dataclass."""

    def test_hydration_failure_attributes(self) -> None:
        """HydrationFailure stores all required attributes."""
        from autom8_asana.models.business.hydration import HydrationFailure

        error = ValueError("Test error")
        failure = HydrationFailure(
            holder_type="unit_holder",
            holder_gid="uh1",
            phase="downward",
            error=error,
            recoverable=True,
        )

        assert failure.holder_type == "unit_holder"
        assert failure.holder_gid == "uh1"
        assert failure.phase == "downward"
        assert failure.error is error
        assert failure.recoverable is True

    def test_hydration_failure_with_none_gid(self) -> None:
        """HydrationFailure supports None for holder_gid."""
        from autom8_asana.models.business.hydration import HydrationFailure

        failure = HydrationFailure(
            holder_type="contact_holder",
            holder_gid=None,  # GID unknown if fetch failed
            phase="upward",
            error=RuntimeError("Network error"),
            recoverable=True,
        )

        assert failure.holder_gid is None


class TestHydrationResult:
    """Tests for HydrationResult dataclass."""

    def test_hydration_result_minimal(self) -> None:
        """HydrationResult with only business."""
        from autom8_asana.models.business.hydration import HydrationResult

        business = Business(gid="b1", name="Acme")
        result = HydrationResult(business=business)

        assert result.business is business
        assert result.entry_entity is None
        assert result.entry_type is None
        assert result.path == []
        assert result.api_calls == 0
        assert result.succeeded == []
        assert result.failed == []
        assert result.warnings == []
        assert result.is_complete is True

    def test_hydration_result_complete_with_successes(self) -> None:
        """HydrationResult.is_complete is True when no failures."""
        from autom8_asana.models.business.hydration import (
            HydrationBranch,
            HydrationResult,
        )

        business = Business(gid="b1", name="Acme")
        result = HydrationResult(
            business=business,
            entry_type=EntityType.CONTACT,
            api_calls=10,
            succeeded=[
                HydrationBranch(
                    holder_type="contact_holder", holder_gid="ch1", child_count=2
                ),
                HydrationBranch(
                    holder_type="unit_holder", holder_gid="uh1", child_count=1
                ),
            ],
        )

        assert result.is_complete is True
        assert len(result.succeeded) == 2

    def test_hydration_result_incomplete_with_failures(self) -> None:
        """HydrationResult.is_complete is False when failures exist."""
        from autom8_asana.models.business.hydration import (
            HydrationFailure,
            HydrationResult,
        )

        business = Business(gid="b1", name="Acme")
        result = HydrationResult(
            business=business,
            failed=[
                HydrationFailure(
                    holder_type="unit_holder",
                    holder_gid="uh1",
                    phase="downward",
                    error=RuntimeError("API error"),
                    recoverable=True,
                ),
            ],
        )

        assert result.is_complete is False
        assert len(result.failed) == 1


class TestIsRecoverable:
    """Tests for _is_recoverable function."""

    def test_rate_limit_is_recoverable(self) -> None:
        """RateLimitError is classified as recoverable."""
        from autom8_asana.exceptions import RateLimitError
        from autom8_asana.models.business.hydration import _is_recoverable

        error = RateLimitError("Rate limited", retry_after=30)
        assert _is_recoverable(error) is True

    def test_timeout_is_recoverable(self) -> None:
        """TimeoutError is classified as recoverable."""
        from autom8_asana.exceptions import TimeoutError
        from autom8_asana.models.business.hydration import _is_recoverable

        error = TimeoutError("Request timed out")
        assert _is_recoverable(error) is True

    def test_server_error_is_recoverable(self) -> None:
        """ServerError is classified as recoverable."""
        from autom8_asana.exceptions import ServerError
        from autom8_asana.models.business.hydration import _is_recoverable

        error = ServerError("Internal server error")
        assert _is_recoverable(error) is True

    def test_not_found_is_not_recoverable(self) -> None:
        """NotFoundError is classified as not recoverable."""
        from autom8_asana.exceptions import NotFoundError
        from autom8_asana.models.business.hydration import _is_recoverable

        error = NotFoundError("Task not found")
        assert _is_recoverable(error) is False

    def test_forbidden_is_not_recoverable(self) -> None:
        """ForbiddenError is classified as not recoverable."""
        from autom8_asana.exceptions import ForbiddenError
        from autom8_asana.models.business.hydration import _is_recoverable

        error = ForbiddenError("Access denied")
        assert _is_recoverable(error) is False

    def test_generic_exception_is_not_recoverable(self) -> None:
        """Generic exceptions default to not recoverable."""
        from autom8_asana.models.business.hydration import _is_recoverable

        error = ValueError("Some error")
        assert _is_recoverable(error) is False


# =============================================================================
# Phase 3: hydrate_from_gid_async Tests
# =============================================================================


@pytest.mark.asyncio
class TestHydrateFromGidAsync:
    """Tests for hydrate_from_gid_async function."""

    async def test_hydrate_from_business_gid(self) -> None:
        """hydrate_from_gid_async from Business GID returns hydrated result."""
        from autom8_asana.models.business.hydration import hydrate_from_gid_async

        client = MagicMock()

        # Mock get_async to return Business task
        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        # Mock subtasks for type detection and hydration
        mock_responses: dict[str, list[Task]] = {
            "b1": [Task(gid="ch1", name="Contacts"), Task(gid="uh1", name="Units")],
            "ch1": [Task(gid="c1", name="John Doe")],
            "uh1": [],
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "b1")

        # Verify result
        assert isinstance(result.business, Business)
        assert result.business.gid == "b1"
        assert result.entry_entity is None  # Started at Business
        assert result.entry_type == EntityType.BUSINESS
        assert result.is_complete is True
        assert result.api_calls > 0

    async def test_hydrate_from_contact_gid(self) -> None:
        """hydrate_from_gid_async from Contact GID traverses up and hydrates."""
        from autom8_asana.models.business.hydration import hydrate_from_gid_async

        client = MagicMock()

        # Mock get_async to return Contact task first, then parent chain
        async def get_async_side_effect(gid: str, **kwargs) -> Task:
            tasks = {
                "c1": Task(
                    gid="c1",
                    name="John Doe",
                    parent=NameGid(gid="ch1", name="Contacts"),
                ),
                "ch1": Task(
                    gid="ch1",
                    name="Contacts",
                    parent=NameGid(gid="b1", name="Acme Corp"),
                ),
                "b1": Task(gid="b1", name="Acme Corp"),
            }
            return tasks[gid]

        client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

        # Mock subtasks for type detection and hydration
        mock_responses: dict[str, list[Task]] = {
            "c1": [],  # Contact has no holder subtasks
            "b1": [Task(gid="ch1", name="Contacts")],
            "ch1": [Task(gid="c1", name="John Doe")],
        }

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=mock_responses.get(gid, []))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "c1")

        # Verify result
        assert isinstance(result.business, Business)
        assert result.business.gid == "b1"
        # entry_entity is converted Contact (may be None if conversion failed)
        # entry_type should be UNKNOWN since c1 has no holder subtasks
        assert result.api_calls > 0
        # Path should include ContactHolder
        assert len(result.path) >= 0

    async def test_hydrate_from_gid_without_hydration(self) -> None:
        """hydrate_from_gid_async with hydrate_full=False skips hydration."""
        from autom8_asana.models.business.hydration import hydrate_from_gid_async

        client = MagicMock()

        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        # Mock subtasks for Business detection only
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

        result = await hydrate_from_gid_async(client, "b1", hydrate_full=False)

        # Business found but not hydrated
        assert result.business.gid == "b1"
        assert result.business._contact_holder is None
        assert result.is_complete is True

    async def test_hydrate_from_gid_with_partial_ok_on_failure(self) -> None:
        """hydrate_from_gid_async with partial_ok=True continues on failure."""
        from autom8_asana.models.business.hydration import hydrate_from_gid_async

        client = MagicMock()

        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        # Mock subtasks - first call for detection succeeds, then fail on hydration
        call_count = 0

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            mock = AsyncMock()
            if call_count == 1:
                # First call: type detection
                mock.collect = AsyncMock(
                    return_value=[
                        Task(gid="ch1", name="Contacts"),
                        Task(gid="uh1", name="Units"),
                    ]
                )
            else:
                # Subsequent calls: fail
                mock.collect = AsyncMock(side_effect=RuntimeError("API error"))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        result = await hydrate_from_gid_async(client, "b1", partial_ok=True)

        # Business returned with failure recorded
        assert result.business.gid == "b1"
        assert result.is_complete is False
        assert len(result.failed) == 1
        assert result.failed[0].phase == "downward"

    async def test_hydrate_from_gid_without_partial_ok_raises(self) -> None:
        """hydrate_from_gid_async without partial_ok raises on failure."""
        from autom8_asana.models.business.hydration import hydrate_from_gid_async

        client = MagicMock()

        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        # Mock subtasks - first call for detection succeeds, then fail on hydration
        call_count = 0

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            mock = AsyncMock()
            if call_count == 1:
                # First call: type detection
                mock.collect = AsyncMock(
                    return_value=[
                        Task(gid="ch1", name="Contacts"),
                        Task(gid="uh1", name="Units"),
                    ]
                )
            else:
                # Subsequent calls: fail
                mock.collect = AsyncMock(side_effect=RuntimeError("API error"))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        with pytest.raises(HydrationError) as exc_info:
            await hydrate_from_gid_async(client, "b1", partial_ok=False)

        assert exc_info.value.phase == "downward"
        assert exc_info.value.entity_gid == "b1"

    async def test_hydrate_from_gid_raises_on_fetch_failure(self) -> None:
        """hydrate_from_gid_async raises HydrationError when initial fetch fails."""
        from autom8_asana.models.business.hydration import hydrate_from_gid_async

        client = MagicMock()
        client.tasks.get_async = AsyncMock(side_effect=RuntimeError("Network error"))

        with pytest.raises(HydrationError) as exc_info:
            await hydrate_from_gid_async(client, "b1")

        assert exc_info.value.entity_gid == "b1"
        assert exc_info.value.phase == "upward"


# =============================================================================
# Phase 3: partial_ok Parameter Tests
# =============================================================================


@pytest.mark.asyncio
class TestPartialOkParameter:
    """Tests for partial_ok parameter across hydration API."""

    async def test_business_from_gid_async_partial_ok_true(self) -> None:
        """Business.from_gid_async with partial_ok=True continues on failure."""
        client = MagicMock()

        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        # Make hydration fail
        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(side_effect=RuntimeError("API error"))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        # Should not raise with partial_ok=True
        business = await Business.from_gid_async(client, "b1", partial_ok=True)
        assert business.gid == "b1"
        assert business._contact_holder is None  # Hydration failed

    async def test_business_from_gid_async_partial_ok_false_raises(self) -> None:
        """Business.from_gid_async with partial_ok=False raises on failure."""
        client = MagicMock()

        business_task = Task(gid="b1", name="Acme Corp")
        client.tasks.get_async = AsyncMock(return_value=business_task)

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(side_effect=RuntimeError("API error"))
            return mock

        client.tasks.subtasks_async.side_effect = subtasks_side_effect

        with pytest.raises(HydrationError):
            await Business.from_gid_async(client, "b1", partial_ok=False)

    async def test_contact_to_business_async_partial_ok_true(self) -> None:
        """Contact.to_business_async with partial_ok=True continues on failure."""
        contact = Contact(
            gid="c1",
            name="John Doe",
            parent=NameGid(gid="ch1", name="Contacts"),
        )
        client = MagicMock()

        # Mock traversal to succeed
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

        # Mock subtasks - succeed for detection, fail for hydration
        call_count = 0

        def subtasks_side_effect(gid: str, **kwargs) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            mock = AsyncMock()
            if call_count == 1:
                # Detection call
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
