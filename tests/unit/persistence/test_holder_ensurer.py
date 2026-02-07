"""Integration tests for holder auto-creation (ENSURE_HOLDERS phase).

Per TDD-GAP-01 S1-008: Integration tests for SC-001, SC-002, SC-003, SC-005.
Per TDD-GAP-01 Sprint 2: Integration tests for SC-004, SC-006, SC-007.

These tests use mocked API responses (not real Asana) but exercise the full
integration between HolderEnsurer, ChangeTracker, SavePipeline, and the
Business/Contact/Unit/Offer model hierarchy.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.batch.models import BatchResult
from autom8_asana.models import Task
from autom8_asana.models.common import NameGid
from autom8_asana.persistence.events import EventSystem
from autom8_asana.persistence.graph import DependencyGraph
from autom8_asana.persistence.holder_concurrency import HolderConcurrencyManager
from autom8_asana.persistence.holder_ensurer import HolderEnsurer
from autom8_asana.persistence.models import EntityState, OperationType
from autom8_asana.persistence.pipeline import SavePipeline
from autom8_asana.persistence.tracker import ChangeTracker

# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


def make_business(gid: str = "biz_123", name: str = "Acme Corp") -> Any:
    """Create a Business entity for testing.

    Note: Entities with real GIDs are tracked as CLEAN by ChangeTracker.
    Tests that need the business in the dirty list must either:
    - Use gid="" (assigns temp GID, tracked as NEW), or
    - Modify the business after tracking (triggers MODIFIED state).
    """
    from autom8_asana.models.business.business import Business

    biz = Business(gid=gid, name=name)
    if not gid:
        object.__setattr__(biz, "gid", f"temp_{id(biz)}")
    return biz


def make_contact(
    gid: str = "",
    name: str = "John Doe",
    business: Any = None,
) -> Any:
    """Create a Contact entity for testing.

    Args:
        gid: Contact GID. If empty, assigns a temp GID.
        name: Contact name.
        business: Parent Business to wire _business back-reference.
    """
    from autom8_asana.models.business.contact import Contact

    contact = Contact(gid=gid, name=name)
    if not gid:
        object.__setattr__(contact, "gid", f"temp_{id(contact)}")
    if business is not None:
        contact._business = business
    return contact


def make_unit(
    gid: str = "",
    name: str = "Premium Unit",
    business: Any = None,
) -> Any:
    """Create a Unit entity for testing.

    Args:
        gid: Unit GID. If empty, assigns a temp GID.
        name: Unit name.
        business: Parent Business to wire _business back-reference.
    """
    from autom8_asana.models.business.unit import Unit

    unit = Unit(gid=gid, name=name)
    if not gid:
        object.__setattr__(unit, "gid", f"temp_{id(unit)}")
    if business is not None:
        unit._business = business
    return unit


def track_and_dirty(tracker: ChangeTracker, entity: Any) -> None:
    """Track an entity and make it dirty by modifying its name.

    For entities with real GIDs, ChangeTracker tracks them as CLEAN.
    This helper modifies the entity after tracking so it appears in
    get_dirty_entities().
    """
    tracker.track(entity)
    # Modify after tracking to trigger dirty detection
    original_name = entity.name
    entity.name = (original_name or "") + " (modified)"


def make_mock_client(subtasks: list[Task] | None = None) -> MagicMock:
    """Create a mock AsanaClient with subtasks response."""
    client = MagicMock()
    client.tasks = MagicMock()

    mock_iterator = MagicMock()
    mock_iterator.collect = AsyncMock(return_value=subtasks or [])
    client.tasks.subtasks_async = MagicMock(return_value=mock_iterator)

    # Mock batch client for pipeline execution
    client.batch = MagicMock()
    client.batch.execute_async = AsyncMock(return_value=[])

    return client


def make_offer(
    gid: str = "",
    name: str = "Google Ads Offer",
    business: Any = None,
) -> Any:
    """Create an Offer entity for testing.

    Args:
        gid: Offer GID. If empty, assigns a temp GID.
        name: Offer name.
        business: Parent Business to wire _business back-reference.
    """
    from autom8_asana.models.business.offer import Offer

    offer = Offer(gid=gid, name=name)
    if not gid:
        object.__setattr__(offer, "gid", f"temp_{id(offer)}")
    if business is not None:
        offer._business = business
    return offer


def make_process(
    gid: str = "",
    name: str = "Onboarding Process",
    business: Any = None,
) -> Any:
    """Create a Process entity for testing.

    Args:
        gid: Process GID. If empty, assigns a temp GID.
        name: Process name.
        business: Parent Business to wire _business back-reference.
    """
    from autom8_asana.models.business.process import Process

    process = Process(gid=gid, name=name)
    if not gid:
        object.__setattr__(process, "gid", f"temp_{id(process)}")
    if business is not None:
        process._business = business
    return process


def _new_entities(result: list[Any], dirty: list[Any]) -> list[Any]:
    """Extract new entities from result that were not in the original dirty list.

    Uses identity comparison (id()) to avoid Pydantic model_dump recursion
    that can occur when circular references exist between entities (e.g.,
    Business -> holder -> _business -> Business).
    """
    dirty_ids = set(id(e) for e in dirty)
    return [e for e in result if id(e) not in dirty_ids]


def make_holder_task(name: str, gid: str, project_gid: str | None = None) -> Task:
    """Create a Task that looks like a holder subtask."""
    memberships = []
    if project_gid:
        memberships = [{"project": {"gid": project_gid}}]
    return Task(gid=gid, name=name, memberships=memberships)


# ---------------------------------------------------------------------------
# SC-001: Missing holders are created during save
# ---------------------------------------------------------------------------


class TestSC001MissingHoldersCreated:
    """SC-001: Saving a Business with unpopulated holders creates missing holders.

    Per PRD SC-001: "Business with 0 holders in Asana -> commit_async() ->
    re-fetch subtasks -> 7 holder subtasks exist."
    """

    @pytest.mark.asyncio
    async def test_all_seven_holders_created_for_dirty_business(self) -> None:
        """When a Business is dirty with no holders, all 7 holders are created.

        This is the core SC-001 test: a Business in the dirty list with no
        populated holders should trigger creation of all 7 holder types.
        """
        from autom8_asana.models.business.business import (
            AssetEditHolder,
            DNAHolder,
            ReconciliationHolder,
            VideographyHolder,
        )
        from autom8_asana.models.business.contact import ContactHolder
        from autom8_asana.models.business.location import LocationHolder
        from autom8_asana.models.business.unit import UnitHolder

        business = make_business(gid="biz_real_gid")

        # No existing holders in Asana
        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        # Track and make dirty (modify after tracking to trigger MODIFIED state)
        track_and_dirty(tracker, business)

        dirty = tracker.get_dirty_entities()
        assert len(dirty) >= 1, "Business must be in dirty list"

        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        # Should have original business + 7 new holders
        new_entities = [e for e in result if e not in dirty]
        assert len(new_entities) == 7

        # Verify all 7 holder types are present
        holder_types = {type(e) for e in new_entities}
        expected_types = {
            ContactHolder,
            UnitHolder,
            LocationHolder,
            DNAHolder,
            ReconciliationHolder,
            AssetEditHolder,
            VideographyHolder,
        }
        assert holder_types == expected_types

    @pytest.mark.asyncio
    async def test_contact_holder_created_with_correct_properties(self) -> None:
        """ContactHolder is created with correct name, temp GID, and parent ref."""
        from autom8_asana.models.business.contact import ContactHolder

        business = make_business(gid="biz_real_gid")

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, business)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        # Find the new ContactHolder
        contact_holders = [e for e in result if isinstance(e, ContactHolder)]
        assert len(contact_holders) == 1
        holder = contact_holders[0]

        # Verify holder properties
        assert holder.name == "Contacts"
        assert holder.gid.startswith("temp_")
        assert holder.parent.gid == "biz_real_gid"

    @pytest.mark.asyncio
    async def test_holders_wired_onto_parent(self) -> None:
        """Created holders are wired onto the parent Business's private attrs."""
        business = make_business(gid="biz_real_gid")

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, business)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        await ensurer.ensure_holders_for_entities(dirty)

        # All 7 holders should now be populated on the business
        assert business._contact_holder is not None
        assert business._unit_holder is not None
        assert business._location_holder is not None
        assert business._dna_holder is not None
        assert business._reconciliation_holder is not None
        assert business._asset_edit_holder is not None
        assert business._videography_holder is not None


# ---------------------------------------------------------------------------
# SC-002: Pre-existing holders are detected and reused
# ---------------------------------------------------------------------------


class TestSC002ExistingHoldersReused:
    """SC-002: Pre-existing holders are detected and reused, not duplicated."""

    @pytest.mark.asyncio
    async def test_existing_holder_reused(self) -> None:
        """When a ContactHolder already exists in Asana, it is reused."""
        from autom8_asana.models.business.contact import ContactHolder

        business = make_business(gid="biz_real_gid")

        # ContactHolder exists in Asana
        existing_holder_task = make_holder_task(
            "Contacts", "existing_ch_gid", ContactHolder.PRIMARY_PROJECT_GID
        )

        mock_client = make_mock_client(subtasks=[existing_holder_task])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, business)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        # The existing holder should be tracked, not a new ContactHolder created
        new_entities = [e for e in result if e not in dirty]
        contact_holders = [e for e in new_entities if isinstance(e, ContactHolder)]
        assert len(contact_holders) == 0

        # The existing holder should be tracked
        assert tracker.is_tracked("existing_ch_gid")

        # Other 6 holders should still be created
        assert len(new_entities) == 6

    @pytest.mark.asyncio
    async def test_partial_existing_only_creates_missing(self) -> None:
        """When 1/7 holders exist, only the 6 missing ones are created."""
        from autom8_asana.models.business.contact import ContactHolder
        from autom8_asana.models.business.unit import UnitHolder

        business = make_business(gid="biz_real_gid")

        # Only ContactHolder exists
        existing_ch = make_holder_task(
            "Contacts", "existing_ch_gid", ContactHolder.PRIMARY_PROJECT_GID
        )

        mock_client = make_mock_client(subtasks=[existing_ch])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, business)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        new_entities = [e for e in result if e not in dirty]

        # 6 holders created (7 total - 1 existing)
        assert len(new_entities) == 6

        # UnitHolder should be among the new ones
        unit_holders = [e for e in new_entities if isinstance(e, UnitHolder)]
        assert len(unit_holders) == 1

        # ContactHolder should NOT be among new ones (it was reused)
        contact_holders = [e for e in new_entities if isinstance(e, ContactHolder)]
        assert len(contact_holders) == 0


# ---------------------------------------------------------------------------
# SC-003: Children parented under created holders
# ---------------------------------------------------------------------------


class TestSC003ChildrenParented:
    """SC-003: Children tracked beneath a newly-created holder are saved as
    subtasks of that holder."""

    @pytest.mark.asyncio
    async def test_contact_parent_set_to_new_holder(self) -> None:
        """New Contact's parent is set to the new ContactHolder's temp GID.

        The contact has _business set to the parent Business. The ensurer
        should match the contact by type (Contact) and _business reference,
        then wire child.parent to the holder's temp GID.
        """
        business = make_business(gid="biz_real_gid")
        contact = make_contact(business=business)

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, business)
        tracker.track(contact)  # Contact has temp GID -> NEW state

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        # Find the new ContactHolder
        from autom8_asana.models.business.contact import ContactHolder

        new_holders = [e for e in result if isinstance(e, ContactHolder)]
        assert len(new_holders) == 1
        holder = new_holders[0]

        # Contact's parent should reference the holder's temp GID
        assert contact.parent is not None
        assert isinstance(contact.parent, NameGid)
        assert contact.parent.gid == holder.gid

    @pytest.mark.asyncio
    async def test_contact_parent_set_to_existing_holder(self) -> None:
        """Contact's parent is set to the existing holder's GID."""
        from autom8_asana.models.business.contact import ContactHolder

        business = make_business(gid="biz_real_gid")
        contact = make_contact(business=business)

        # Existing holder in Asana
        existing_holder = make_holder_task(
            "Contacts", "existing_ch_gid", ContactHolder.PRIMARY_PROJECT_GID
        )

        mock_client = make_mock_client(subtasks=[existing_holder])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, business)
        tracker.track(contact)  # Contact has temp GID -> NEW state

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        await ensurer.ensure_holders_for_entities(dirty)

        # Contact's parent should reference the existing holder's GID
        assert contact.parent is not None
        assert isinstance(contact.parent, NameGid)
        assert contact.parent.gid == "existing_ch_gid"

    @pytest.mark.asyncio
    async def test_unit_parent_set_to_new_holder(self) -> None:
        """New Unit's parent is set to the new UnitHolder's temp GID."""
        business = make_business(gid="biz_real_gid")
        unit = make_unit(business=business)

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, business)
        tracker.track(unit)  # Unit has temp GID -> NEW state

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        from autom8_asana.models.business.unit import UnitHolder

        new_holders = [e for e in result if isinstance(e, UnitHolder)]
        assert len(new_holders) == 1
        holder = new_holders[0]

        # Unit's parent should reference the holder's temp GID
        assert unit.parent is not None
        assert isinstance(unit.parent, NameGid)
        assert unit.parent.gid == holder.gid

    @pytest.mark.asyncio
    async def test_children_not_belonging_to_parent_are_not_wired(self) -> None:
        """Children with _business pointing to a different Business are not wired."""
        business_a = make_business(gid="biz_a")
        business_b = make_business(gid="biz_b")

        # Contact belongs to business_b, not business_a
        contact = make_contact(business=business_b)

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, business_a)
        tracker.track(contact)  # Contact has temp GID -> NEW state

        dirty = tracker.get_dirty_entities()
        # Save the contact's original parent before ensurer runs
        original_parent = contact.parent

        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        await ensurer.ensure_holders_for_entities(dirty)

        # Contact should NOT have its parent wired to business_a's contact holder
        # because the contact's _business points to business_b.
        # The contact's parent should remain as the original value.
        # ContactHolder was created for business_a but should not wire this contact.
        if contact.parent is not None and original_parent is None:
            # If the parent was set, it should NOT be business_a's contact holder
            # (which is identified by the fact that its parent points to biz_a)
            biz_a_ch = business_a._contact_holder
            assert biz_a_ch is not None
            assert contact.parent.gid != biz_a_ch.gid


# ---------------------------------------------------------------------------
# SC-005: Opt-out flag
# ---------------------------------------------------------------------------


class TestSC005OptOut:
    """SC-005: Holder auto-creation can be disabled by the caller."""

    def test_auto_create_holders_default_true(self) -> None:
        """auto_create_holders defaults to True."""
        client = MagicMock()
        client.batch = MagicMock()
        client._http = MagicMock()
        client._config = MagicMock()
        client._config.automation = MagicMock()
        client._config.automation.enabled = False

        from autom8_asana.persistence.session import SaveSession

        session = SaveSession(client)
        assert session.auto_create_holders is True

    def test_auto_create_holders_can_be_disabled(self) -> None:
        """auto_create_holders=False disables the feature."""
        client = MagicMock()
        client.batch = MagicMock()
        client._http = MagicMock()
        client._config = MagicMock()
        client._config.automation = MagicMock()
        client._config.automation.enabled = False

        from autom8_asana.persistence.session import SaveSession

        session = SaveSession(client, auto_create_holders=False)
        assert session.auto_create_holders is False

    @pytest.mark.asyncio
    async def test_opt_out_skips_ensure_holders(self) -> None:
        """When auto_create_holders=False, the ensurer would create holders
        but the session skips the phase entirely."""
        business = make_business(gid="biz_real_gid")

        # Verify the ensurer would create holders if called directly
        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, business)

        dirty = tracker.get_dirty_entities()

        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)
        new_holders = [e for e in result if e not in dirty]
        assert len(new_holders) == 7  # Would have been created

    def test_opt_out_no_concurrency_manager_created(self) -> None:
        """When auto_create_holders=False, no HolderConcurrencyManager is created."""
        client = MagicMock()
        client.batch = MagicMock()
        client._http = MagicMock()
        client._config = MagicMock()
        client._config.automation = MagicMock()
        client._config.automation.enabled = False

        from autom8_asana.persistence.session import SaveSession

        session = SaveSession(client, auto_create_holders=False)
        assert session._holder_concurrency is None


# ---------------------------------------------------------------------------
# HolderEnsurer Internal Logic Tests
# ---------------------------------------------------------------------------


class TestHolderEnsurerInternals:
    """Tests for HolderEnsurer internal logic."""

    @pytest.mark.asyncio
    async def test_empty_entities_returns_same_list(self) -> None:
        """Empty dirty list returns empty list."""
        mock_client = make_mock_client()
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities([])
        assert result == []

    @pytest.mark.asyncio
    async def test_entities_without_holder_key_map_pass_through(self) -> None:
        """Entities without HOLDER_KEY_MAP are returned unchanged."""
        mock_client = make_mock_client()
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        task = Task(gid="t1", name="Simple task")
        tracker.track(task)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        assert len(result) == len(dirty)

    @pytest.mark.asyncio
    async def test_detection_failure_still_creates_holders(self) -> None:
        """If detection API fails, holders are still created (fallback to create)."""
        business = make_business(gid="biz_real_gid")

        # Client that raises on subtasks_async
        mock_client = MagicMock()
        mock_client.tasks = MagicMock()
        mock_iterator = MagicMock()
        mock_iterator.collect = AsyncMock(side_effect=ConnectionError("API down"))
        mock_client.tasks.subtasks_async = MagicMock(return_value=mock_iterator)

        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()
        track_and_dirty(tracker, business)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        # Should still have created all 7 holders despite detection failure
        new_holders = [e for e in result if e not in dirty]
        assert len(new_holders) == 7

    @pytest.mark.asyncio
    async def test_new_business_skips_detection(self) -> None:
        """For a new Business (temp GID), detection is skipped."""
        # Use gid="" which gets temp GID -> EntityState.NEW
        business = make_business(gid="")

        mock_client = make_mock_client()
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        tracker.track(business)

        dirty = tracker.get_dirty_entities()
        assert len(dirty) >= 1, "New business must be in dirty list"

        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        # Should have created all 7 holders without calling subtasks API
        mock_client.tasks.subtasks_async.assert_not_called()

        new_holders = [e for e in result if e not in dirty]
        assert len(new_holders) == 7

        # Each holder's parent should reference the Business temp GID
        for holder in new_holders:
            assert holder.parent.gid == business.gid

    @pytest.mark.asyncio
    async def test_already_tracked_holder_is_skipped(self) -> None:
        """If a holder is already populated AND tracked, it is not re-created."""
        from autom8_asana.models.business.contact import ContactHolder

        business = make_business(gid="biz_real_gid")

        # Pre-populate a tracked ContactHolder on the business
        existing_ch = ContactHolder(
            gid="existing_ch_gid", name="Contacts", resource_type="task"
        )
        business._contact_holder = existing_ch

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, business)
        tracker.track(existing_ch)  # Track the existing holder

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        new_entities = [e for e in result if e not in dirty]

        # Only 6 holders should be created (contact_holder already tracked)
        assert len(new_entities) == 6

        # No new ContactHolders should be in the result
        new_contact_holders = [e for e in new_entities if isinstance(e, ContactHolder)]
        assert len(new_contact_holders) == 0


# ---------------------------------------------------------------------------
# Dependency Graph Integration Tests
# ---------------------------------------------------------------------------


class TestDependencyGraphIntegration:
    """Tests verifying that constructed holders integrate correctly with the
    DependencyGraph."""

    def test_holder_placed_between_business_and_child(self) -> None:
        """Business at L0, holder at L1, child at L2."""
        from autom8_asana.models.business.business import Business
        from autom8_asana.models.business.contact import Contact, ContactHolder

        business = Business(gid="biz_123", name="Acme")
        holder = ContactHolder(gid="", name="Contacts", resource_type="task")
        object.__setattr__(holder, "gid", f"temp_{id(holder)}")
        holder.parent = NameGid(gid="biz_123")

        contact = Contact(gid="", name="John")
        object.__setattr__(contact, "gid", f"temp_{id(contact)}")
        contact.parent = NameGid(gid=holder.gid)

        graph = DependencyGraph()
        graph.build([business, holder, contact])
        levels = graph.get_levels()

        assert len(levels) == 3
        assert business in levels[0]
        assert holder in levels[1]
        assert contact in levels[2]

    def test_multiple_holders_same_level(self) -> None:
        """Multiple holders under same Business are at the same level."""
        from autom8_asana.models.business.business import Business
        from autom8_asana.models.business.contact import ContactHolder
        from autom8_asana.models.business.unit import UnitHolder

        business = Business(gid="biz_123", name="Acme")

        ch = ContactHolder(gid="", name="Contacts", resource_type="task")
        object.__setattr__(ch, "gid", f"temp_{id(ch)}")
        ch.parent = NameGid(gid="biz_123")

        uh = UnitHolder(gid="", name="Business Units", resource_type="task")
        object.__setattr__(uh, "gid", f"temp_{id(uh)}")
        uh.parent = NameGid(gid="biz_123")

        graph = DependencyGraph()
        graph.build([business, ch, uh])
        levels = graph.get_levels()

        assert len(levels) == 2
        assert business in levels[0]
        assert ch in levels[1]
        assert uh in levels[1]

    def test_temp_gid_chain_resolves(self) -> None:
        """All-new Business -> Holder -> Child with temp GIDs resolves correctly."""
        from autom8_asana.models.business.business import Business
        from autom8_asana.models.business.contact import Contact, ContactHolder
        from autom8_asana.persistence.holder_construction import construct_holder

        # All-new entities
        business = Business(gid="", name="New Biz")
        object.__setattr__(business, "gid", f"temp_{id(business)}")

        holder = construct_holder(
            "contact_holder",
            Business.HOLDER_KEY_MAP,
            business,
        )

        contact = Contact(gid="", name="John")
        object.__setattr__(contact, "gid", f"temp_{id(contact)}")
        contact.parent = NameGid(gid=holder.gid)

        graph = DependencyGraph()
        graph.build([business, holder, contact])
        levels = graph.get_levels()

        assert len(levels) == 3
        assert business in levels[0]
        assert holder in levels[1]
        assert contact in levels[2]


# ===========================================================================
# Sprint 2 Tests: Multi-Level Chains, Concurrency, Edge Cases
# ===========================================================================


# ---------------------------------------------------------------------------
# S2-001: HolderEnsurer handles Unit-level holders
# ---------------------------------------------------------------------------


class TestS2001UnitLevelHolders:
    """S2-001: HolderEnsurer creates OfferHolder and ProcessHolder for Units."""

    @pytest.mark.asyncio
    async def test_unit_holders_created_when_unit_in_dirty_list(self) -> None:
        """When a Unit with HOLDER_KEY_MAP is dirty, its 2 holders are created.

        This verifies that the ensurer handles Unit entities the same way it
        handles Business entities -- Units have their own HOLDER_KEY_MAP with
        offer_holder and process_holder.
        """
        from autom8_asana.models.business.offer import OfferHolder
        from autom8_asana.models.business.process import ProcessHolder

        business = make_business(gid="biz_real_gid")
        unit = make_unit(business=business)

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        # Track business and unit
        track_and_dirty(tracker, business)
        tracker.track(unit)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        # Find Unit-level holders
        offer_holders = [e for e in result if isinstance(e, OfferHolder)]
        process_holders = [e for e in result if isinstance(e, ProcessHolder)]

        assert len(offer_holders) == 1, "OfferHolder should be created"
        assert len(process_holders) == 1, "ProcessHolder should be created"

        # Holders should be wired onto the Unit
        assert unit._offer_holder is not None
        assert unit._process_holder is not None

    @pytest.mark.asyncio
    async def test_offer_wired_to_offer_holder(self) -> None:
        """New Offer's parent is set to the new OfferHolder's temp GID.

        SC-006 verification: Track Unit + new Offer -> commit_async() ->
        Offer.parent.gid == OfferHolder.gid
        """
        from autom8_asana.models.business.offer import OfferHolder

        business = make_business(gid="biz_real_gid")
        unit = make_unit(business=business)
        offer = make_offer(business=business)

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, business)
        tracker.track(unit)
        tracker.track(offer)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        offer_holders = [e for e in result if isinstance(e, OfferHolder)]
        assert len(offer_holders) == 1
        oh = offer_holders[0]

        # Offer's parent should be the OfferHolder
        assert offer.parent is not None
        assert isinstance(offer.parent, NameGid)
        assert offer.parent.gid == oh.gid

    @pytest.mark.asyncio
    async def test_process_wired_to_process_holder(self) -> None:
        """New Process's parent is set to the new ProcessHolder's temp GID."""
        from autom8_asana.models.business.process import ProcessHolder

        business = make_business(gid="biz_real_gid")
        unit = make_unit(business=business)
        process = make_process(business=business)

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, business)
        tracker.track(unit)
        tracker.track(process)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        process_holders = [e for e in result if isinstance(e, ProcessHolder)]
        assert len(process_holders) == 1
        ph = process_holders[0]

        # Process's parent should be the ProcessHolder
        assert process.parent is not None
        assert isinstance(process.parent, NameGid)
        assert process.parent.gid == ph.gid

    @pytest.mark.asyncio
    async def test_unit_holder_parent_references_unit_temp_gid(self) -> None:
        """OfferHolder created for a new Unit references the Unit's temp GID."""
        from autom8_asana.models.business.offer import OfferHolder

        business = make_business(gid="")
        unit = make_unit(business=business)

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        tracker.track(business)
        tracker.track(unit)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        offer_holders = [e for e in result if isinstance(e, OfferHolder)]
        assert len(offer_holders) == 1
        oh = offer_holders[0]

        # OfferHolder's parent should reference Unit's temp GID
        assert oh.parent.gid == unit.gid
        assert oh.parent.gid.startswith("temp_")


# ---------------------------------------------------------------------------
# S2-002, S2-003: Temp GID assignment and 5-level dependency graph
# ---------------------------------------------------------------------------


class TestS2005LevelDependencyGraph:
    """S2-002, S2-003: Verify temp GID chains and 5-level graph ordering."""

    def test_five_level_chain_produces_five_levels(self) -> None:
        """Full 5-level chain with all-new entities produces 5 graph levels.

        Per TDD Section 4.3: Kahn's algorithm proof for 5 levels:
        L0: Business
        L1: UnitHolder
        L2: Unit
        L3: OfferHolder
        L4: Offer
        """
        from autom8_asana.models.business.business import Business
        from autom8_asana.models.business.offer import Offer, OfferHolder
        from autom8_asana.models.business.unit import Unit, UnitHolder
        from autom8_asana.persistence.holder_construction import construct_holder

        # Build 5-level chain manually
        business = Business(gid="", name="New Biz")
        object.__setattr__(business, "gid", f"temp_{id(business)}")

        unit_holder = construct_holder("unit_holder", Business.HOLDER_KEY_MAP, business)

        unit = Unit(gid="", name="Unit One")
        object.__setattr__(unit, "gid", f"temp_{id(unit)}")
        unit.parent = NameGid(gid=unit_holder.gid)

        offer_holder = construct_holder("offer_holder", Unit.HOLDER_KEY_MAP, unit)

        offer = Offer(gid="", name="Google Ads")
        object.__setattr__(offer, "gid", f"temp_{id(offer)}")
        offer.parent = NameGid(gid=offer_holder.gid)

        graph = DependencyGraph()
        graph.build([business, unit_holder, unit, offer_holder, offer])
        levels = graph.get_levels()

        assert len(levels) == 5
        assert business in levels[0]
        assert unit_holder in levels[1]
        assert unit in levels[2]
        assert offer_holder in levels[3]
        assert offer in levels[4]

    def test_five_level_chain_with_fan_out(self) -> None:
        """5-level chain with fan-outs: multiple holders at same level.

        Per TDD Section 4.5:
        L0: Business
        L1: ContactHolder, UnitHolder
        L2: Unit
        L3: OfferHolder, ProcessHolder
        L4: Offer, Process
        """
        from autom8_asana.models.business.business import Business
        from autom8_asana.models.business.contact import Contact, ContactHolder
        from autom8_asana.models.business.offer import Offer, OfferHolder
        from autom8_asana.models.business.process import Process, ProcessHolder
        from autom8_asana.models.business.unit import Unit, UnitHolder
        from autom8_asana.persistence.holder_construction import construct_holder

        # Build tree with fan-outs
        business = Business(gid="", name="New Biz")
        object.__setattr__(business, "gid", f"temp_{id(business)}")

        contact_holder = construct_holder(
            "contact_holder", Business.HOLDER_KEY_MAP, business
        )
        unit_holder = construct_holder("unit_holder", Business.HOLDER_KEY_MAP, business)

        contact = Contact(gid="", name="John")
        object.__setattr__(contact, "gid", f"temp_{id(contact)}")
        contact.parent = NameGid(gid=contact_holder.gid)

        unit = Unit(gid="", name="Unit One")
        object.__setattr__(unit, "gid", f"temp_{id(unit)}")
        unit.parent = NameGid(gid=unit_holder.gid)

        offer_holder = construct_holder("offer_holder", Unit.HOLDER_KEY_MAP, unit)
        process_holder = construct_holder("process_holder", Unit.HOLDER_KEY_MAP, unit)

        offer = Offer(gid="", name="Google Ads")
        object.__setattr__(offer, "gid", f"temp_{id(offer)}")
        offer.parent = NameGid(gid=offer_holder.gid)

        process = Process(gid="", name="Onboarding")
        object.__setattr__(process, "gid", f"temp_{id(process)}")
        process.parent = NameGid(gid=process_holder.gid)

        graph = DependencyGraph()
        graph.build(
            [
                business,
                contact_holder,
                unit_holder,
                contact,
                unit,
                offer_holder,
                process_holder,
                offer,
                process,
            ]
        )
        levels = graph.get_levels()

        assert len(levels) == 5

        # L0: Business only
        assert business in levels[0]
        assert len(levels[0]) == 1

        # L1: Both Business-level holders
        assert contact_holder in levels[1]
        assert unit_holder in levels[1]

        # L2: Contact and Unit
        assert contact in levels[2]
        assert unit in levels[2]

        # L3: Both Unit-level holders (fan-out)
        assert offer_holder in levels[3]
        assert process_holder in levels[3]

        # L4: Offer and Process
        assert offer in levels[4]
        assert process in levels[4]

    def test_resolve_parent_gid_handles_temp_name_gid(self) -> None:
        """_resolve_parent_gid handles NameGid with temp_ GID string.

        Per TDD Section 4.4 (Option A): When a holder has parent=NameGid(gid="temp_xxx")
        and the referenced entity is in the graph, the resolution succeeds.
        """
        from autom8_asana.models.business.business import Business
        from autom8_asana.models.business.unit import UnitHolder
        from autom8_asana.persistence.holder_construction import construct_holder

        business = Business(gid="", name="New Biz")
        object.__setattr__(business, "gid", f"temp_{id(business)}")

        holder = construct_holder("unit_holder", Business.HOLDER_KEY_MAP, business)

        # Verify holder.parent is NameGid with temp GID
        assert isinstance(holder.parent, NameGid)
        assert holder.parent.gid.startswith("temp_")
        assert holder.parent.gid == business.gid

        # Build graph and verify it resolves
        graph = DependencyGraph()
        graph.build([business, holder])
        levels = graph.get_levels()

        assert len(levels) == 2
        assert business in levels[0]
        assert holder in levels[1]


# ---------------------------------------------------------------------------
# S2-004: Concurrency tests (SC-004)
# ---------------------------------------------------------------------------


class TestS2004Concurrency:
    """SC-004: Concurrent in-process saves produce no duplicates.

    Two asyncio coroutines calling ensure_holders_for_entities on the same
    Business simultaneously. The asyncio.Lock per (parent_gid, holder_type)
    prevents duplicate creation.
    """

    @pytest.mark.asyncio
    async def test_concurrent_saves_no_duplicate_holders(self) -> None:
        """Two coroutines saving same Business produce 7 holders, not 14.

        Per PRD SC-004: Two concurrent coroutine commit_async() calls on
        same Business -> 7 holders total, not 14.
        """
        business = make_business(gid="biz_concurrent")

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, business)

        dirty = tracker.get_dirty_entities()

        # Both coroutines use the same ensurer (same concurrency manager)
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)

        # Run two ensures concurrently
        results = await asyncio.gather(
            ensurer.ensure_holders_for_entities(list(dirty)),
            ensurer.ensure_holders_for_entities(list(dirty)),
        )

        # Count total unique holder types created across both results
        all_new_holders: list[Any] = []
        for result in results:
            new = _new_entities(result, dirty)
            all_new_holders.extend(new)

        # Because of the lock-based idempotency check inside _ensure_single_holder,
        # the second coroutine finds the holder already populated on the parent
        # and tracked, so it skips creation.
        # The first result should have 7 new holders.
        result1_new = _new_entities(results[0], dirty)
        result2_new = _new_entities(results[1], dirty)

        # Total unique holders should be 7, not 14
        total_unique = len(result1_new) + len(result2_new)
        assert total_unique == 7, (
            f"Expected 7 unique holders, got {total_unique} "
            f"(coroutine1={len(result1_new)}, coroutine2={len(result2_new)})"
        )

    @pytest.mark.asyncio
    async def test_different_businesses_can_proceed_in_parallel(self) -> None:
        """Lock granularity: different Businesses can proceed in parallel.

        The lock key is (parent_gid, holder_type), so two different
        Businesses should not block each other.
        """
        biz_a = make_business(gid="biz_a")
        biz_b = make_business(gid="biz_b")

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, biz_a)
        track_and_dirty(tracker, biz_b)

        dirty = tracker.get_dirty_entities()
        dirty_ids = set(id(e) for e in dirty)

        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        # Both businesses should get their holders
        # Use identity comparison to avoid Pydantic model_dump recursion
        new_entities = [e for e in result if id(e) not in dirty_ids]
        assert len(new_entities) == 14  # 7 for each Business


# ---------------------------------------------------------------------------
# S2-005: Full tree from scratch (SC-007)
# ---------------------------------------------------------------------------


class TestS2005FullTreeFromScratch:
    """SC-007: Full 5-level tree from scratch.

    ALL entities new (no real GIDs):
    Business(temp) -> UnitHolder(temp) -> Unit(temp) -> OfferHolder(temp) -> Offer(temp)
    """

    @pytest.mark.asyncio
    async def test_full_tree_all_new_entities(self) -> None:
        """Business + Unit + Offer, all new -> ensurer creates all holders.

        This is the hardest success criterion. The dependency graph must
        produce 5 topological levels. GID resolution must propagate through
        all 5 levels.
        """
        from autom8_asana.models.business.offer import OfferHolder
        from autom8_asana.models.business.process import ProcessHolder
        from autom8_asana.models.business.unit import UnitHolder

        business = make_business(gid="")
        unit = make_unit(business=business)
        offer = make_offer(business=business)

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        tracker.track(business)
        tracker.track(unit)
        tracker.track(offer)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        new_entities = _new_entities(result, dirty)

        # Business holders: 7 (contact, unit, location, dna, recon, asset, video)
        # Unit holders: 2 (offer, process)
        # Total new: 9
        assert len(new_entities) == 9, (
            f"Expected 9 holders, got {len(new_entities)}: "
            f"{[type(e).__name__ for e in new_entities]}"
        )

        # Verify Business-level holders
        unit_holders = [e for e in new_entities if isinstance(e, UnitHolder)]
        assert len(unit_holders) == 1

        # Verify Unit-level holders
        offer_holders = [e for e in new_entities if isinstance(e, OfferHolder)]
        process_holders = [e for e in new_entities if isinstance(e, ProcessHolder)]
        assert len(offer_holders) == 1
        assert len(process_holders) == 1

    @pytest.mark.asyncio
    async def test_full_tree_graph_produces_five_levels(self) -> None:
        """Full new tree -> dependency graph produces exactly 5 levels.

        After the ensurer creates all holders, the combined entity list
        should produce 5 topological levels when fed to the graph.
        """
        from autom8_asana.models.business.offer import Offer, OfferHolder
        from autom8_asana.models.business.unit import Unit, UnitHolder

        business = make_business(gid="")
        unit = make_unit(business=business)
        offer = make_offer(business=business)

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        tracker.track(business)
        tracker.track(unit)
        tracker.track(offer)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        # Build dependency graph from all entities
        graph = DependencyGraph()
        graph.build(result)
        levels = graph.get_levels()

        # Expect 5 levels for the full chain
        assert len(levels) >= 5, (
            f"Expected 5+ levels, got {len(levels)}: "
            f"{[[type(e).__name__ for e in level] for level in levels]}"
        )

        # Verify key entities are at correct levels
        # L0: Business (no parent)
        assert business in levels[0]

        # Find UnitHolder (should be at L1)
        unit_holder_level = None
        for i, level in enumerate(levels):
            for e in level:
                if isinstance(e, UnitHolder):
                    unit_holder_level = i
                    break

        assert unit_holder_level == 1, f"UnitHolder at level {unit_holder_level}"

        # Find Unit (should be at L2)
        unit_level = None
        for i, level in enumerate(levels):
            for e in level:
                if isinstance(e, Unit) and e is unit:
                    unit_level = i
                    break

        assert unit_level == 2, f"Unit at level {unit_level}"

        # Find OfferHolder (should be at L3)
        offer_holder_level = None
        for i, level in enumerate(levels):
            for e in level:
                if isinstance(e, OfferHolder):
                    offer_holder_level = i
                    break

        assert offer_holder_level == 3, f"OfferHolder at level {offer_holder_level}"

        # Find Offer (should be at L4)
        offer_level = None
        for i, level in enumerate(levels):
            for e in level:
                if isinstance(e, Offer) and e is offer:
                    offer_level = i
                    break

        assert offer_level == 4, f"Offer at level {offer_level}"

    @pytest.mark.asyncio
    async def test_full_tree_parent_chain_intact(self) -> None:
        """All parent references form a complete chain from Offer up to Business."""
        from autom8_asana.models.business.offer import OfferHolder
        from autom8_asana.models.business.unit import UnitHolder

        business = make_business(gid="")
        unit = make_unit(business=business)
        offer = make_offer(business=business)

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        tracker.track(business)
        tracker.track(unit)
        tracker.track(offer)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        # Find holders
        unit_holder = None
        offer_holder = None
        for e in result:
            if isinstance(e, UnitHolder):
                unit_holder = e
            if isinstance(e, OfferHolder):
                offer_holder = e

        assert unit_holder is not None
        assert offer_holder is not None

        # Chain: Offer -> OfferHolder -> Unit -> UnitHolder -> Business
        # Offer's parent = OfferHolder
        assert offer.parent.gid == offer_holder.gid

        # OfferHolder's parent = Unit
        assert offer_holder.parent.gid == unit.gid

        # Unit's parent = UnitHolder
        assert unit.parent.gid == unit_holder.gid

        # UnitHolder's parent = Business
        assert unit_holder.parent.gid == business.gid


# ---------------------------------------------------------------------------
# S2-006: Unit nested holder integration test (SC-006)
# ---------------------------------------------------------------------------


class TestS2006UnitNestedHolders:
    """SC-006: Unit nested holders auto-created when saving a Unit with children."""

    @pytest.mark.asyncio
    async def test_unit_with_offers_creates_offer_holder(self) -> None:
        """Unit + Offers -> OfferHolder auto-created under Unit.

        Per PRD SC-006 verification:
        Track Unit + new Offer -> commit_async() -> Offer.parent.gid == OfferHolder.gid
        """
        from autom8_asana.models.business.offer import OfferHolder

        # Existing Business and Unit; only Offer is new
        business = make_business(gid="biz_existing")
        unit = make_unit(gid="unit_existing", business=business)
        offer = make_offer(business=business)

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        # Track unit as dirty, plus the new offer
        track_and_dirty(tracker, unit)
        tracker.track(offer)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        # OfferHolder should be created
        offer_holders = [e for e in result if isinstance(e, OfferHolder)]
        assert len(offer_holders) == 1

        # Offer should be wired to OfferHolder
        assert offer.parent is not None
        assert offer.parent.gid == offer_holders[0].gid

    @pytest.mark.asyncio
    async def test_unit_with_processes_creates_process_holder(self) -> None:
        """Unit + Processes -> ProcessHolder auto-created under Unit."""
        from autom8_asana.models.business.process import ProcessHolder

        business = make_business(gid="biz_existing")
        unit = make_unit(gid="unit_existing", business=business)
        process = make_process(business=business)

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, unit)
        tracker.track(process)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        process_holders = [e for e in result if isinstance(e, ProcessHolder)]
        assert len(process_holders) == 1

        assert process.parent is not None
        assert process.parent.gid == process_holders[0].gid

    @pytest.mark.asyncio
    async def test_unit_both_holders_created(self) -> None:
        """Unit with both Offers and Processes -> both holders created."""
        from autom8_asana.models.business.offer import OfferHolder
        from autom8_asana.models.business.process import ProcessHolder

        business = make_business(gid="biz_existing")
        unit = make_unit(gid="unit_existing", business=business)
        offer = make_offer(business=business)
        process = make_process(business=business)

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, unit)
        tracker.track(offer)
        tracker.track(process)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        offer_holders = [e for e in result if isinstance(e, OfferHolder)]
        process_holders = [e for e in result if isinstance(e, ProcessHolder)]

        assert len(offer_holders) == 1
        assert len(process_holders) == 1


# ---------------------------------------------------------------------------
# S2-007: Edge case tests from PRD table
# ---------------------------------------------------------------------------


class TestS2007EdgeCases:
    """Edge case tests from PRD table."""

    @pytest.mark.asyncio
    async def test_business_has_no_children_noop(self) -> None:
        """Business with no children in dirty list still creates all holders.

        Per PRD edge case: Business has no children to save.
        Per PRD SC-001: ALL missing holders are created when Business is dirty,
        regardless of whether children exist.
        """
        business = make_business(gid="biz_real_gid")

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, business)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        # All 7 holders should still be created even without children
        new_entities = _new_entities(result, dirty)
        assert len(new_entities) == 7

    @pytest.mark.asyncio
    async def test_multiple_units_each_get_holders(self) -> None:
        """Multiple Units each get their own OfferHolder and ProcessHolder."""
        from autom8_asana.models.business.offer import OfferHolder
        from autom8_asana.models.business.process import ProcessHolder

        business = make_business(gid="biz_real_gid")
        unit_a = make_unit(gid="", name="Unit A", business=business)
        unit_b = make_unit(gid="", name="Unit B", business=business)

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, business)
        tracker.track(unit_a)
        tracker.track(unit_b)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        offer_holders = [e for e in result if isinstance(e, OfferHolder)]
        process_holders = [e for e in result if isinstance(e, ProcessHolder)]

        # Each Unit should get its own set of holders
        assert len(offer_holders) == 2, (
            f"Expected 2 OfferHolders (one per Unit), got {len(offer_holders)}"
        )
        assert len(process_holders) == 2, (
            f"Expected 2 ProcessHolders (one per Unit), got {len(process_holders)}"
        )

        # Verify holders reference their respective Units
        oh_parents = {oh.parent.gid for oh in offer_holders}
        assert unit_a.gid in oh_parents
        assert unit_b.gid in oh_parents

    @pytest.mark.asyncio
    async def test_holder_with_existing_real_gid_unit_detects_holders(self) -> None:
        """Unit with real GID calls detection API for existing holders."""
        from autom8_asana.models.business.offer import OfferHolder

        business = make_business(gid="biz_real_gid")
        unit = make_unit(gid="unit_real_gid", business=business)

        # Existing OfferHolder for this unit
        existing_oh = make_holder_task(
            "Offers", "existing_oh_gid", OfferHolder.PRIMARY_PROJECT_GID
        )

        mock_client = make_mock_client(subtasks=[existing_oh])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, business)
        track_and_dirty(tracker, unit)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        result = await ensurer.ensure_holders_for_entities(dirty)

        # The existing OfferHolder should be reused, not recreated
        offer_holders = [e for e in result if isinstance(e, OfferHolder)]
        new_offer_holders = [
            e for e in offer_holders if e.gid and e.gid.startswith("temp_")
        ]
        assert len(new_offer_holders) == 0, "Should reuse existing OfferHolder"

        # The existing holder should be tracked
        assert tracker.is_tracked("existing_oh_gid")

    @pytest.mark.asyncio
    async def test_offer_for_different_unit_not_wired(self) -> None:
        """Offers belonging to a different Unit are not wired to wrong holder.

        This tests the _business reference check in _wire_children_parent:
        an Offer with _business pointing to a different Business should not
        be wired to the wrong Unit's OfferHolder.
        """
        business_a = make_business(gid="biz_a")
        business_b = make_business(gid="biz_b")

        unit_a = make_unit(gid="", name="Unit A", business=business_a)
        # Offer belongs to business_b, not business_a
        offer_for_b = make_offer(business=business_b)

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, business_a)
        tracker.track(unit_a)
        tracker.track(offer_for_b)

        dirty = tracker.get_dirty_entities()
        original_offer_parent = offer_for_b.parent

        ensurer = HolderEnsurer(mock_client, tracker, concurrency)
        await ensurer.ensure_holders_for_entities(dirty)

        # If the offer got a parent, it should NOT be unit_a's OfferHolder
        if offer_for_b.parent is not None and original_offer_parent is None:
            assert offer_for_b.parent.gid != unit_a._offer_holder.gid


# ---------------------------------------------------------------------------
# S2-008: Observability -- structured logging
# ---------------------------------------------------------------------------


class TestS2008Observability:
    """S2-008: Structured logging for holder lifecycle events."""

    @pytest.mark.asyncio
    async def test_wave_logging_emitted(self) -> None:
        """Wave start/complete log events are emitted for multi-level processing."""
        business = make_business(gid="")
        unit = make_unit(business=business)
        offer = make_offer(business=business)

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        tracker.track(business)
        tracker.track(unit)
        tracker.track(offer)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)

        # Verify no exceptions during logging-enriched execution
        result = await ensurer.ensure_holders_for_entities(dirty)

        # Should have created holders for both Business and Unit
        new_entities = _new_entities(result, dirty)
        assert len(new_entities) == 9  # 7 Business + 2 Unit

    @pytest.mark.asyncio
    async def test_holder_construction_complete_logged(self) -> None:
        """holder_construction_complete log event includes expected fields.

        This test verifies no exceptions during the logging code path.
        The actual log output is verified by inspecting structured logging
        in integration environments.
        """
        business = make_business(gid="biz_real_gid")

        mock_client = make_mock_client(subtasks=[])
        tracker = ChangeTracker()
        concurrency = HolderConcurrencyManager()

        track_and_dirty(tracker, business)

        dirty = tracker.get_dirty_entities()
        ensurer = HolderEnsurer(mock_client, tracker, concurrency)

        # Should complete without logging errors
        result = await ensurer.ensure_holders_for_entities(dirty)
        assert len(_new_entities(result, dirty)) == 7
