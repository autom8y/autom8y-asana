"""Tests for EventTransport implementations.

Per GAP-03 NFR-003: InMemoryTransport for unit testing.
"""

from __future__ import annotations

import pytest

from autom8_asana.automation.events.envelope import EventEnvelope
from autom8_asana.automation.events.transport import InMemoryTransport
from autom8_asana.automation.events.types import EventType


def _make_envelope(
    event_type: EventType = EventType.CREATED,
    entity_gid: str = "123",
) -> EventEnvelope:
    return EventEnvelope.build(
        event_type=event_type,
        entity_type="Process",
        entity_gid=entity_gid,
        source="test",
    )


class TestInMemoryTransport:
    """Test InMemoryTransport stores and retrieves envelopes."""

    @pytest.mark.asyncio
    async def test_publish_stores_envelope(self) -> None:
        transport = InMemoryTransport()
        envelope = _make_envelope()

        await transport.publish(envelope, "test://queue")

        assert transport.count == 1
        assert transport.published[0] == (envelope, "test://queue")

    @pytest.mark.asyncio
    async def test_publish_multiple(self) -> None:
        transport = InMemoryTransport()
        e1 = _make_envelope(entity_gid="1")
        e2 = _make_envelope(entity_gid="2")

        await transport.publish(e1, "dest-a")
        await transport.publish(e2, "dest-b")

        assert transport.count == 2

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        transport = InMemoryTransport()
        await transport.publish(_make_envelope(), "dest")

        transport.clear()

        assert transport.count == 0

    @pytest.mark.asyncio
    async def test_get_envelopes_all(self) -> None:
        transport = InMemoryTransport()
        e1 = _make_envelope(EventType.CREATED)
        e2 = _make_envelope(EventType.UPDATED)

        await transport.publish(e1, "dest")
        await transport.publish(e2, "dest")

        result = transport.get_envelopes()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_envelopes_filtered(self) -> None:
        transport = InMemoryTransport()
        e1 = _make_envelope(EventType.CREATED)
        e2 = _make_envelope(EventType.UPDATED)
        e3 = _make_envelope(EventType.CREATED)

        await transport.publish(e1, "dest")
        await transport.publish(e2, "dest")
        await transport.publish(e3, "dest")

        created = transport.get_envelopes(event_type="created")
        assert len(created) == 2
        assert all(e.event_type == EventType.CREATED for e in created)

    @pytest.mark.asyncio
    async def test_get_envelopes_filtered_empty(self) -> None:
        transport = InMemoryTransport()
        await transport.publish(_make_envelope(EventType.CREATED), "dest")

        result = transport.get_envelopes(event_type="deleted")
        assert len(result) == 0
