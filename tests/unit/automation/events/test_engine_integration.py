"""Integration tests for EventEmissionRule with AutomationEngine.

Per GAP-03: Verify emission rules work within the engine evaluation loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from autom8_asana.automation.base import TriggerCondition
from autom8_asana.automation.config import AutomationConfig
from autom8_asana.automation.engine import AutomationEngine
from autom8_asana.automation.events.config import EventRoutingConfig, SubscriptionEntry
from autom8_asana.automation.events.emitter import EventEmitter
from autom8_asana.automation.events.rule import EventEmissionRule
from autom8_asana.automation.events.transport import InMemoryTransport
from autom8_asana.automation.events.types import EventType
from autom8_asana.persistence.models import AutomationResult, SaveResult

if TYPE_CHECKING:
    from autom8_asana.automation.context import AutomationContext
    from autom8_asana.automation.events.envelope import EventEnvelope


class MockEntity:
    def __init__(self, gid: str = "123456") -> None:
        self.gid = gid
        self._is_new = False


class MockNewEntity:
    def __init__(self, gid: str = "temp_999") -> None:
        self.gid = gid
        self._is_new = True


class CountingRule:
    """Rule that counts triggers for verification."""

    def __init__(self) -> None:
        self.trigger_count = 0
        self.execute_count = 0

    @property
    def id(self) -> str:
        return "counting_rule"

    @property
    def name(self) -> str:
        return "Counting Rule"

    @property
    def trigger(self) -> TriggerCondition:
        return TriggerCondition(entity_type="*", event="*")

    def should_trigger(self, entity: Any, event: str, context: dict[str, Any]) -> bool:
        self.trigger_count += 1
        return True

    async def execute_async(self, entity: Any, context: AutomationContext) -> AutomationResult:
        self.execute_count += 1
        return AutomationResult(
            rule_id=self.id,
            rule_name=self.name,
            triggered_by_gid=entity.gid,
            triggered_by_type=type(entity).__name__,
            success=True,
        )


@pytest.fixture
def transport() -> InMemoryTransport:
    return InMemoryTransport()


@pytest.fixture
def enabled_emitter(transport: InMemoryTransport) -> EventEmitter:
    config = EventRoutingConfig(
        enabled=True,
        subscriptions=[SubscriptionEntry(destination="test://events")],
    )
    return EventEmitter(transport=transport, config=config)


@pytest.fixture
def disabled_emitter(transport: InMemoryTransport) -> EventEmitter:
    config = EventRoutingConfig(enabled=False)
    return EventEmitter(transport=transport, config=config)


class TestEngineWithEmissionRule:
    """Test emission rule integrated with AutomationEngine."""

    async def test_emission_rule_triggered_by_engine(
        self,
        enabled_emitter: EventEmitter,
        transport: InMemoryTransport,
    ) -> None:
        """Emission rule triggers alongside other rules."""
        engine = AutomationEngine(AutomationConfig())
        emission_rule = EventEmissionRule(emitter=enabled_emitter)
        counting_rule = CountingRule()

        engine.register(counting_rule)
        engine.register(emission_rule)

        entity = MockEntity(gid="test-123")
        save_result = SaveResult(succeeded=[entity])
        client = MagicMock()

        results = await engine.evaluate_async(save_result, client)

        # Both rules triggered
        assert len(results) == 2
        assert counting_rule.execute_count == 1
        assert transport.count == 1

        # Verify envelope content
        envelope = transport.published[0][0]
        assert envelope.entity_gid == "test-123"
        assert envelope.event_type == EventType.UPDATED  # existing entity

    async def test_emission_failure_does_not_affect_other_rules(
        self,
        transport: InMemoryTransport,
    ) -> None:
        """Pipeline rule succeeds even if emission fails."""

        class FailTransport:
            async def publish(self, envelope: EventEnvelope, dest: str) -> None:
                raise ConnectionError("transport down")

        config = EventRoutingConfig(
            enabled=True,
            subscriptions=[SubscriptionEntry(destination="test://events")],
        )
        fail_emitter = EventEmitter(transport=FailTransport(), config=config)

        engine = AutomationEngine(AutomationConfig())
        counting_rule = CountingRule()
        emission_rule = EventEmissionRule(emitter=fail_emitter)

        engine.register(counting_rule)
        engine.register(emission_rule)

        entity = MockEntity()
        save_result = SaveResult(succeeded=[entity])
        client = MagicMock()

        results = await engine.evaluate_async(save_result, client)

        # Both rules executed
        assert len(results) == 2
        # Counting rule succeeded
        assert results[0].success is True
        # Emission rule also reports success (transport failures are non-fatal)
        assert results[1].success is True

    async def test_emission_disabled_no_transport_call(
        self,
        disabled_emitter: EventEmitter,
        transport: InMemoryTransport,
    ) -> None:
        """EVENTS_ENABLED=false means no publish called."""
        engine = AutomationEngine(AutomationConfig())
        emission_rule = EventEmissionRule(emitter=disabled_emitter)
        engine.register(emission_rule)

        entity = MockEntity()
        save_result = SaveResult(succeeded=[entity])
        client = MagicMock()

        results = await engine.evaluate_async(save_result, client)

        # Rule's should_trigger returned False, so not in results
        assert len(results) == 0
        assert transport.count == 0

    async def test_new_entity_detected_as_created(
        self,
        enabled_emitter: EventEmitter,
        transport: InMemoryTransport,
    ) -> None:
        engine = AutomationEngine(AutomationConfig())
        emission_rule = EventEmissionRule(emitter=enabled_emitter)
        engine.register(emission_rule)

        entity = MockNewEntity()
        save_result = SaveResult(succeeded=[entity])
        client = MagicMock()

        results = await engine.evaluate_async(save_result, client)

        assert len(results) == 1
        envelope = transport.published[0][0]
        assert envelope.event_type == EventType.CREATED
