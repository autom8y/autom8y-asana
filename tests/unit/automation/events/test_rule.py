"""Tests for EventEmissionRule.

Per GAP-03 SC-001: Emission rules are triggered by SaveSession commits.
Per SC-004: Emission failures do not propagate.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from autom8_asana.automation.config import AutomationConfig
from autom8_asana.automation.context import AutomationContext
from autom8_asana.automation.events.config import EventRoutingConfig, SubscriptionEntry
from autom8_asana.automation.events.emitter import EventEmitter
from autom8_asana.automation.events.envelope import EventEnvelope
from autom8_asana.automation.events.rule import EventEmissionRule
from autom8_asana.automation.events.transport import InMemoryTransport
from autom8_asana.automation.events.types import EventType
from autom8_asana.persistence.models import SaveResult


class MockEntity:
    def __init__(self, gid: str = "123456", entity_type: str = "Process") -> None:
        self.gid = gid
        self.__class__.__name__ = entity_type  # type: ignore[attr-defined]


class MockProcess:
    """Mock Process with process_type."""

    def __init__(self, gid: str = "123456") -> None:
        self.gid = gid
        self.process_type = MagicMock(value="sales")


@pytest.fixture
def transport() -> InMemoryTransport:
    return InMemoryTransport()


@pytest.fixture
def config() -> EventRoutingConfig:
    return EventRoutingConfig(
        enabled=True,
        subscriptions=[SubscriptionEntry(destination="test://events")],
    )


@pytest.fixture
def disabled_config() -> EventRoutingConfig:
    return EventRoutingConfig(
        enabled=False,
        subscriptions=[SubscriptionEntry(destination="test://events")],
    )


@pytest.fixture
def emitter(transport: InMemoryTransport, config: EventRoutingConfig) -> EventEmitter:
    return EventEmitter(transport=transport, config=config)


@pytest.fixture
def disabled_emitter(
    transport: InMemoryTransport, disabled_config: EventRoutingConfig
) -> EventEmitter:
    return EventEmitter(transport=transport, config=disabled_config)


@pytest.fixture
def context() -> AutomationContext:
    return AutomationContext(
        client=MagicMock(),
        config=AutomationConfig(),
        save_result=SaveResult(succeeded=[]),
    )


class TestShouldTrigger:
    """Test should_trigger method."""

    def test_enabled_returns_true(self, emitter: EventEmitter) -> None:
        rule = EventEmissionRule(emitter=emitter)
        entity = MockEntity()
        result = rule.should_trigger(entity, EventType.CREATED, {})
        assert result is True

    def test_disabled_returns_false(self, disabled_emitter: EventEmitter) -> None:
        rule = EventEmissionRule(emitter=disabled_emitter)
        entity = MockEntity()
        result = rule.should_trigger(entity, EventType.CREATED, {})
        assert result is False

    def test_filtered_subscription_matches(self, transport: InMemoryTransport) -> None:
        config = EventRoutingConfig(
            enabled=True,
            subscriptions=[
                SubscriptionEntry(
                    event_types=["section_changed"],
                    destination="test://events",
                ),
            ],
        )
        emitter = EventEmitter(transport=transport, config=config)
        rule = EventEmissionRule(emitter=emitter)
        entity = MockEntity()

        assert rule.should_trigger(entity, EventType.SECTION_CHANGED, {}) is True
        assert rule.should_trigger(entity, EventType.CREATED, {}) is False


class TestExecuteAsync:
    """Test execute_async method."""

    @pytest.mark.asyncio
    async def test_builds_envelope_and_emits(
        self,
        emitter: EventEmitter,
        transport: InMemoryTransport,
        context: AutomationContext,
    ) -> None:
        """SC-001: Emission rules triggered by commits."""
        rule = EventEmissionRule(emitter=emitter)
        entity = MockEntity(gid="999")

        rule.should_trigger(entity, EventType.CREATED, {})
        result = await rule.execute_async(entity, context)

        assert result.success is True
        assert result.rule_id == "event_emission"
        assert "emit_event" in result.actions_executed
        assert transport.count == 1

        envelope = transport.published[0][0]
        assert envelope.event_type == EventType.CREATED
        assert envelope.entity_gid == "999"
        assert envelope.source == "save_session"

    @pytest.mark.asyncio
    async def test_transport_failure_returns_success(
        self,
        context: AutomationContext,
    ) -> None:
        """SC-004: Emission failures do not propagate."""

        class FailTransport:
            async def publish(
                self, envelope: EventEnvelope, destination: str
            ) -> None:
                raise ConnectionError("down")

        config = EventRoutingConfig(
            enabled=True,
            subscriptions=[SubscriptionEntry(destination="test://events")],
        )
        emitter = EventEmitter(transport=FailTransport(), config=config)
        rule = EventEmissionRule(emitter=emitter)
        entity = MockEntity()

        rule.should_trigger(entity, EventType.UPDATED, {})
        result = await rule.execute_async(entity, context)

        # Rule succeeds even though transport failed
        assert result.success is True
        assert result.enhancement_results["events_failed"] == 1

    @pytest.mark.asyncio
    async def test_payload_includes_process_type(
        self,
        emitter: EventEmitter,
        transport: InMemoryTransport,
        context: AutomationContext,
    ) -> None:
        rule = EventEmissionRule(emitter=emitter)
        entity = MockProcess(gid="555")

        rule.should_trigger(entity, EventType.CREATED, {})
        await rule.execute_async(entity, context)

        envelope = transport.published[0][0]
        assert envelope.payload["process_type"] == "sales"

    @pytest.mark.asyncio
    async def test_unknown_event_type_skipped(
        self,
        emitter: EventEmitter,
        transport: InMemoryTransport,
        context: AutomationContext,
    ) -> None:
        rule = EventEmissionRule(emitter=emitter)
        entity = MockEntity()

        # Force an unknown event type
        rule._last_event = "totally_unknown"
        result = await rule.execute_async(entity, context)

        assert result.success is True
        assert result.skipped_reason is not None
        assert "unknown_event_type" in result.skipped_reason
        assert transport.count == 0

    @pytest.mark.asyncio
    async def test_enhancement_results_tracking(
        self,
        emitter: EventEmitter,
        transport: InMemoryTransport,
        context: AutomationContext,
    ) -> None:
        rule = EventEmissionRule(emitter=emitter)
        entity = MockEntity()

        rule.should_trigger(entity, EventType.UPDATED, {})
        result = await rule.execute_async(entity, context)

        assert result.enhancement_results["events_attempted"] == 1
        assert result.enhancement_results["events_succeeded"] == 1
        assert result.enhancement_results["events_failed"] == 0

    def test_rule_properties(self, emitter: EventEmitter) -> None:
        rule = EventEmissionRule(emitter=emitter)
        assert rule.id == "event_emission"
        assert rule.name == "Event Emission"
        assert rule.trigger.entity_type == "*"
        assert rule.trigger.event == "*"
