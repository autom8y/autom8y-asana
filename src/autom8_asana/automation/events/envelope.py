"""Event envelope for external publication.

Per GAP-03 FR-002: Structured event envelope with required fields.
Per ADR-GAP03-003: Thin payloads (GID + metadata only).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from autom8_asana.automation.events.types import EventType


@dataclass(frozen=True)
class EventEnvelope:
    """Immutable event envelope for external publication.

    Attributes:
        schema_version: Envelope format version for forward compatibility.
        event_id: UUID serving as idempotency key.
        event_type: From EventType enum.
        entity_type: String name of entity class (e.g., "Process", "Offer").
        entity_gid: Asana GID of affected entity.
        timestamp: ISO 8601 UTC timestamp of event detection.
        source: Origin identifier (e.g., "save_session", "webhook_inbound").
        correlation_id: End-to-end trace ID for cross-service loop detection.
        causation_id: ID of the event that caused this event.
        payload: Event-type-specific metadata (thin: GID + context only).
    """

    schema_version: str
    event_id: str
    event_type: EventType
    entity_type: str
    entity_gid: str
    timestamp: str
    source: str
    correlation_id: str
    causation_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "entity_type": self.entity_type,
            "entity_gid": self.entity_gid,
            "timestamp": self.timestamp,
            "source": self.source,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "payload": self.payload,
        }

    @staticmethod
    def build(
        event_type: EventType,
        entity_type: str,
        entity_gid: str,
        source: str,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> EventEnvelope:
        """Factory method to build envelope with auto-generated fields.

        Args:
            event_type: The type of event.
            entity_type: Entity class name.
            entity_gid: Asana GID.
            source: Origin identifier.
            correlation_id: Optional trace ID. Generated if not provided.
            causation_id: Optional cause event ID.
            payload: Optional event-specific metadata.

        Returns:
            New EventEnvelope with generated event_id and timestamp.
        """
        return EventEnvelope(
            schema_version="1.0",
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            entity_type=entity_type,
            entity_gid=entity_gid,
            timestamp=datetime.now(UTC).isoformat(),
            source=source,
            correlation_id=correlation_id or str(uuid.uuid4()),
            causation_id=causation_id,
            payload=payload or {},
        )
