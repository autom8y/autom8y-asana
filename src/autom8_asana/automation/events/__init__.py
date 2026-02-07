"""Event routing and external publication.

Per GAP-03: Provides event type vocabulary, envelope schema,
transport abstraction, and emission rules for external consumers.

Usage:
    from autom8_asana.automation.events import setup_event_emission

    # Register event emission with engine (reads EVENTS_* env vars)
    setup_event_emission(engine)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.automation.events.config import (
    EventRoutingConfig,
    SubscriptionEntry,
)
from autom8_asana.automation.events.emitter import EmitResult, EventEmitter
from autom8_asana.automation.events.envelope import EventEnvelope
from autom8_asana.automation.events.rule import EventEmissionRule
from autom8_asana.automation.events.transport import (
    EventTransport,
    InMemoryTransport,
    SQSTransport,
)
from autom8_asana.automation.events.types import EventType

if TYPE_CHECKING:
    from autom8_asana.automation.engine import AutomationEngine

logger = get_logger(__name__)

__all__ = [
    "EventType",
    "EventEnvelope",
    "EventTransport",
    "InMemoryTransport",
    "SQSTransport",
    "EventEmitter",
    "EmitResult",
    "EventEmissionRule",
    "EventRoutingConfig",
    "SubscriptionEntry",
    "setup_event_emission",
]


def setup_event_emission(engine: AutomationEngine) -> bool:
    """Register EventEmissionRule with an AutomationEngine.

    Reads configuration from environment variables (EVENTS_ENABLED,
    EVENTS_SQS_QUEUE_URL, EVENTS_SUBSCRIPTIONS). If events are not
    enabled or not configured, does nothing.

    Per ADR-GAP03-005: EVENTS_ENABLED=false by default (no-op).

    Args:
        engine: AutomationEngine to register the emission rule with.

    Returns:
        True if emission rule was registered, False if skipped.
    """
    try:
        config = EventRoutingConfig.from_env()
    except ValueError as e:
        logger.error("event_routing_config_invalid", error=str(e))
        raise

    if not config.enabled:
        logger.debug("event_emission_disabled")
        return False

    # Create transport
    transport = SQSTransport.from_boto3()

    # Create emitter and rule
    emitter = EventEmitter(transport=transport, config=config)
    rule = EventEmissionRule(emitter=emitter)

    engine.register(rule)
    logger.info(
        "event_emission_registered",
        subscriptions=len(config.subscriptions),
    )
    return True
