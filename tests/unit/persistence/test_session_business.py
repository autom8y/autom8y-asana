"""Tests for SaveSession business model extensions.

Per TDD-BIZMODEL: Tests for track() with prefetch_holders and recursive parameters.
Per ADR-0050: Holder lazy loading on track().
Per ADR-0053: Optional recursive=True for composite SaveSession.
"""

from __future__ import annotations

from unittest.mock import MagicMock, AsyncMock

import pytest

from autom8_asana.models import Task
from autom8_asana.persistence.session import SaveSession


def create_mock_client() -> MagicMock:
    """Create a mock AsanaClient with mock batch client."""
    mock_client = MagicMock()
    mock_batch = MagicMock()
    mock_batch.execute_async = AsyncMock(return_value=[])
    mock_client.batch = mock_batch
    mock_client._log = None

    mock_http = AsyncMock()
    mock_http.request = AsyncMock(return_value={"data": {}})
    mock_client._http = mock_http

    return mock_client


class TestTrackExtendedSignature:
    """Tests for track() extended signature (prefetch_holders, recursive)."""

    def test_track_accepts_prefetch_holders_param(self) -> None:
        """track() accepts prefetch_holders parameter."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Test")
        # Should not raise
        result = session.track(task, prefetch_holders=True)

        assert result is task

    def test_track_accepts_recursive_param(self) -> None:
        """track() accepts recursive parameter."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Test")
        # Should not raise
        result = session.track(task, recursive=True)

        assert result is task

    def test_track_accepts_both_params(self) -> None:
        """track() accepts both prefetch_holders and recursive."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Test")
        # Should not raise
        result = session.track(task, prefetch_holders=True, recursive=True)

        assert result is task

    def test_track_defaults_are_false(self) -> None:
        """track() defaults prefetch_holders and recursive to False."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="123", name="Test")
        # Basic track without params should work
        result = session.track(task)

        assert result is task


class TestRecursiveTracking:
    """Tests for track() with recursive=True."""

    def test_recursive_tracks_holder_children(self) -> None:
        """recursive=True tracks entities in holder children lists."""
        from autom8_asana.models.business import Business, ContactHolder, Contact

        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        # Set up hierarchy with valid numeric GIDs
        business = Business(gid="1111111111", name="Test Business")
        holder = ContactHolder(gid="2222222222", name="Contacts")
        contact = Contact(gid="3333333333", name="John Doe")

        holder._contacts = [contact]
        holder._business = business
        contact._contact_holder = holder

        business._contact_holder = holder

        # Track with recursive
        session.track(business, recursive=True)

        # Verify holder and children are tracked by GID (ADR-0078)
        assert session.is_tracked(holder.gid)
        assert session.is_tracked(contact.gid)

    def test_recursive_tracks_unit_hierarchy(self) -> None:
        """recursive=True tracks full Unit -> Offer -> Process hierarchy."""
        from autom8_asana.models.business import (
            Business,
            Unit,
            UnitHolder,
            Offer,
            OfferHolder,
            Process,
            ProcessHolder,
        )

        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        # Set up hierarchy with valid numeric GIDs
        business = Business(gid="1111111111", name="Test Business")
        unit_holder = UnitHolder(gid="2222222222", name="Units")
        unit = Unit(gid="3333333333", name="Test Unit")
        offer_holder = OfferHolder(gid="4444444444", name="Offers")
        offer = Offer(gid="5555555555", name="Test Offer")
        process_holder = ProcessHolder(gid="6666666666", name="Processes")
        process = Process(gid="7777777777", name="Test Process")

        # Wire up hierarchy
        offer_holder._offers = [offer]
        offer_holder._unit = unit
        offer._offer_holder = offer_holder

        process_holder._processes = [process]
        process_holder._unit = unit
        process._process_holder = process_holder

        unit._offer_holder = offer_holder
        unit._process_holder = process_holder
        unit._unit_holder = unit_holder
        unit._business = business

        unit_holder._units = [unit]
        unit_holder._business = business

        business._unit_holder = unit_holder

        # Track with recursive
        session.track(business, recursive=True)

        # Verify full hierarchy is tracked by GID (ADR-0078)
        assert session.is_tracked(unit_holder.gid)
        assert session.is_tracked(unit.gid)
        assert session.is_tracked(offer_holder.gid)
        assert session.is_tracked(offer.gid)
        assert session.is_tracked(process_holder.gid)
        assert session.is_tracked(process.gid)

    def test_recursive_handles_empty_holders(self) -> None:
        """recursive=True handles entities with empty holders."""
        from autom8_asana.models.business import Business, ContactHolder

        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        business = Business(gid="1111111111", name="Test Business")
        holder = ContactHolder(gid="2222222222", name="Contacts")
        holder._contacts = []  # Empty
        holder._business = business
        business._contact_holder = holder

        # Should not raise
        session.track(business, recursive=True)

        # Holder is tracked even if empty (by GID per ADR-0078)
        assert session.is_tracked(holder.gid)

    def test_recursive_handles_none_holders(self) -> None:
        """recursive=True handles entities with None holders."""
        from autom8_asana.models.business import Business

        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        business = Business(gid="1111111111", name="Test Business")
        # All holders are None by default

        # Should not raise
        session.track(business, recursive=True)

        # Business is tracked (by GID per ADR-0078)
        assert session.is_tracked(business.gid)

    def test_non_recursive_does_not_track_children(self) -> None:
        """Without recursive, children are not tracked."""
        from autom8_asana.models.business import Business, ContactHolder, Contact

        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        business = Business(gid="1111111111", name="Test Business")
        holder = ContactHolder(gid="2222222222", name="Contacts")
        contact = Contact(gid="3333333333", name="John Doe")

        holder._contacts = [contact]
        holder._business = business
        business._contact_holder = holder

        # Track WITHOUT recursive
        session.track(business)

        # Only business is tracked (by GID per ADR-0078)
        assert session.is_tracked(business.gid)
        assert not session.is_tracked(holder.gid)
        assert not session.is_tracked(contact.gid)


class TestTrackWithPlainTask:
    """Tests for track() with plain Task entities."""

    def test_recursive_with_plain_task_is_noop(self) -> None:
        """recursive=True with plain Task has no effect."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="1234567890", name="Test Task")

        # Should not raise
        session.track(task, recursive=True)

        # Task is tracked (by GID per ADR-0078)
        assert session.is_tracked(task.gid)

    def test_prefetch_holders_with_plain_task_is_noop(self) -> None:
        """prefetch_holders=True with plain Task has no effect."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="1234567890", name="Test Task")

        # Should not raise
        session.track(task, prefetch_holders=True)

        # Task is tracked (by GID per ADR-0078)
        assert session.is_tracked(task.gid)
