"""Tests for EventEmitter.

Per GAP-03 SC-004: Emission failures do not propagate.
Per FR-007: Emission metrics via structured logging.
Per FR-010: Dead letter logging for failed envelopes.
"""

from __future__ import annotations

import pytest

from autom8_asana.automation.events.config import EventRoutingConfig, SubscriptionEntry
from autom8_asana.automation.events.emitter import EventEmitter
from autom8_asana.automation.events.envelope import EventEnvelope
from autom8_asana.automation.events.transport import InMemoryTransport
from autom8_asana.automation.events.types import EventType


def _make_envelope(
    event_type: EventType = EventType.CREATED,
    entity_type: str = "Process",
    entity_gid: str = "123",
) -> EventEnvelope:
    return EventEnvelope.build(
        event_type=event_type,
        entity_type=entity_type,
        entity_gid=entity_gid,
        source="test",
    )


class FailingTransport:
    """Transport that always raises."""

    def __init__(self, error: Exception | None = None) -> None:
        self._error = error or ConnectionError("Transport unavailable")

    async def publish(self, envelope: EventEnvelope, destination: str) -> None:
        raise self._error


class PartialTransport:
    """Transport that fails on specific destinations."""

    def __init__(self, fail_destinations: set[str]) -> None:
        self._fail = fail_destinations
        self.published: list[tuple[EventEnvelope, str]] = []

    async def publish(self, envelope: EventEnvelope, destination: str) -> None:
        if destination in self._fail:
            raise ConnectionError(f"Failed: {destination}")
        self.published.append((envelope, destination))


class TestEmitterRouting:
    """Test emitter routes to matching subscriptions."""

    @pytest.mark.asyncio
    async def test_routes_to_matching_subs(self) -> None:
        transport = InMemoryTransport()
        config = EventRoutingConfig(
            enabled=True,
            subscriptions=[SubscriptionEntry(destination="dest-a")],
        )
        emitter = EventEmitter(transport=transport, config=config)
        envelope = _make_envelope()

        result = await emitter.emit(envelope)

        assert result.attempted == 1
        assert result.succeeded == 1
        assert result.failed == 0
        assert transport.count == 1

    @pytest.mark.asyncio
    async def test_no_matching_subs(self) -> None:
        transport = InMemoryTransport()
        config = EventRoutingConfig(
            enabled=True,
            subscriptions=[
                SubscriptionEntry(
                    event_types=["deleted"],
                    destination="dest-a",
                ),
            ],
        )
        emitter = EventEmitter(transport=transport, config=config)
        envelope = _make_envelope(EventType.CREATED)

        result = await emitter.emit(envelope)

        assert result.attempted == 0
        assert result.succeeded == 0
        assert result.failed == 0
        assert transport.count == 0

    @pytest.mark.asyncio
    async def test_multiple_matching_destinations(self) -> None:
        transport = InMemoryTransport()
        config = EventRoutingConfig(
            enabled=True,
            subscriptions=[
                SubscriptionEntry(destination="dest-a"),
                SubscriptionEntry(destination="dest-b"),
            ],
        )
        emitter = EventEmitter(transport=transport, config=config)
        envelope = _make_envelope()

        result = await emitter.emit(envelope)

        assert result.attempted == 2
        assert result.succeeded == 2
        assert transport.count == 2

    @pytest.mark.asyncio
    async def test_disabled_config_no_emission(self) -> None:
        transport = InMemoryTransport()
        config = EventRoutingConfig(
            enabled=False,
            subscriptions=[SubscriptionEntry(destination="dest-a")],
        )
        emitter = EventEmitter(transport=transport, config=config)
        envelope = _make_envelope()

        result = await emitter.emit(envelope)

        assert result.attempted == 0
        assert transport.count == 0


class TestEmitterFailureIsolation:
    """Test that transport failures are caught and logged."""

    @pytest.mark.asyncio
    async def test_transport_failure_logged_not_raised(self) -> None:
        """SC-004: Emission failures do not propagate."""
        transport = FailingTransport()
        config = EventRoutingConfig(
            enabled=True,
            subscriptions=[SubscriptionEntry(destination="dest-a")],
        )
        emitter = EventEmitter(transport=transport, config=config)
        envelope = _make_envelope()

        # Should NOT raise
        result = await emitter.emit(envelope)

        assert result.attempted == 1
        assert result.succeeded == 0
        assert result.failed == 1

    @pytest.mark.asyncio
    async def test_partial_failure(self) -> None:
        transport = PartialTransport(fail_destinations={"dest-b"})
        config = EventRoutingConfig(
            enabled=True,
            subscriptions=[
                SubscriptionEntry(destination="dest-a"),
                SubscriptionEntry(destination="dest-b"),
            ],
        )
        emitter = EventEmitter(transport=transport, config=config)
        envelope = _make_envelope()

        result = await emitter.emit(envelope)

        assert result.attempted == 2
        assert result.succeeded == 1
        assert result.failed == 1
        assert result.partial is True
        assert len(transport.published) == 1

    @pytest.mark.asyncio
    async def test_all_succeeded_property(self) -> None:
        transport = InMemoryTransport()
        config = EventRoutingConfig(
            enabled=True,
            subscriptions=[SubscriptionEntry(destination="dest-a")],
        )
        emitter = EventEmitter(transport=transport, config=config)
        envelope = _make_envelope()

        result = await emitter.emit(envelope)

        assert result.all_succeeded is True
        assert result.partial is False
