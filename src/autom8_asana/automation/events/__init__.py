"""Event routing and external publication.

Per GAP-03: Provides event type vocabulary, envelope schema,
transport abstraction, and emission rules for external consumers.
"""

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
]
