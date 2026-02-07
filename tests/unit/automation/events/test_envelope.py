"""Tests for EventEnvelope.

Per GAP-03 SC-002: Event envelope has all required fields.
"""

from __future__ import annotations

import json
import uuid

import pytest

from autom8_asana.automation.events.envelope import EventEnvelope
from autom8_asana.automation.events.types import EventType


class TestEventEnvelopeBuild:
    """Test EventEnvelope.build() factory method."""

    def test_required_fields_present(self) -> None:
        """SC-002: All required fields are present and non-empty."""
        envelope = EventEnvelope.build(
            event_type=EventType.CREATED,
            entity_type="Process",
            entity_gid="1234567890",
            source="save_session",
        )

        assert envelope.schema_version == "1.0"
        assert envelope.event_id  # non-empty
        assert envelope.event_type is EventType.CREATED
        assert envelope.entity_type == "Process"
        assert envelope.entity_gid == "1234567890"
        assert envelope.timestamp  # non-empty
        assert envelope.source == "save_session"
        assert envelope.correlation_id  # auto-generated

    def test_event_id_is_uuid(self) -> None:
        envelope = EventEnvelope.build(
            event_type=EventType.UPDATED,
            entity_type="Offer",
            entity_gid="999",
            source="test",
        )
        # Should parse as UUID without error
        uuid.UUID(envelope.event_id)

    def test_correlation_id_auto_generated(self) -> None:
        envelope = EventEnvelope.build(
            event_type=EventType.CREATED,
            entity_type="Process",
            entity_gid="123",
            source="test",
        )
        uuid.UUID(envelope.correlation_id)

    def test_correlation_id_explicit(self) -> None:
        envelope = EventEnvelope.build(
            event_type=EventType.CREATED,
            entity_type="Process",
            entity_gid="123",
            source="test",
            correlation_id="my-correlation-id",
        )
        assert envelope.correlation_id == "my-correlation-id"

    def test_causation_id_default_none(self) -> None:
        envelope = EventEnvelope.build(
            event_type=EventType.CREATED,
            entity_type="Process",
            entity_gid="123",
            source="test",
        )
        assert envelope.causation_id is None

    def test_causation_id_explicit(self) -> None:
        envelope = EventEnvelope.build(
            event_type=EventType.CREATED,
            entity_type="Process",
            entity_gid="123",
            source="test",
            causation_id="parent-event-id",
        )
        assert envelope.causation_id == "parent-event-id"

    def test_payload_default_empty(self) -> None:
        envelope = EventEnvelope.build(
            event_type=EventType.CREATED,
            entity_type="Process",
            entity_gid="123",
            source="test",
        )
        assert envelope.payload == {}

    def test_payload_explicit(self) -> None:
        envelope = EventEnvelope.build(
            event_type=EventType.SECTION_CHANGED,
            entity_type="Process",
            entity_gid="123",
            source="save_session",
            payload={"section_gid": "456", "process_type": "sales"},
        )
        assert envelope.payload == {"section_gid": "456", "process_type": "sales"}

    def test_timestamp_is_iso8601_utc(self) -> None:
        envelope = EventEnvelope.build(
            event_type=EventType.CREATED,
            entity_type="Process",
            entity_gid="123",
            source="test",
        )
        # Should contain UTC offset indicator
        assert "+00:00" in envelope.timestamp or "Z" in envelope.timestamp


class TestEventEnvelopeToJsonDict:
    """Test JSON serialization."""

    def test_to_json_dict_all_fields(self) -> None:
        envelope = EventEnvelope.build(
            event_type=EventType.SECTION_CHANGED,
            entity_type="Process",
            entity_gid="1234567890",
            source="save_session",
            correlation_id="corr-123",
            causation_id="cause-456",
            payload={"section_gid": "789"},
        )

        d = envelope.to_json_dict()

        assert d["schema_version"] == "1.0"
        assert d["event_type"] == "section_changed"
        assert d["entity_type"] == "Process"
        assert d["entity_gid"] == "1234567890"
        assert d["source"] == "save_session"
        assert d["correlation_id"] == "corr-123"
        assert d["causation_id"] == "cause-456"
        assert d["payload"] == {"section_gid": "789"}

    def test_json_serializable(self) -> None:
        envelope = EventEnvelope.build(
            event_type=EventType.CREATED,
            entity_type="Process",
            entity_gid="123",
            source="test",
        )
        # Should not raise
        result = json.dumps(envelope.to_json_dict())
        assert isinstance(result, str)

    def test_json_roundtrip(self) -> None:
        envelope = EventEnvelope.build(
            event_type=EventType.UPDATED,
            entity_type="Offer",
            entity_gid="456",
            source="webhook_inbound",
            payload={"key": "value"},
        )
        serialized = json.dumps(envelope.to_json_dict())
        deserialized = json.loads(serialized)

        assert deserialized["event_type"] == "updated"
        assert deserialized["entity_type"] == "Offer"
        assert deserialized["payload"]["key"] == "value"


class TestEventEnvelopeImmutability:
    """Test frozen dataclass enforcement."""

    def test_frozen(self) -> None:
        envelope = EventEnvelope.build(
            event_type=EventType.CREATED,
            entity_type="Process",
            entity_gid="123",
            source="test",
        )
        with pytest.raises(AttributeError):
            envelope.event_type = EventType.UPDATED  # type: ignore[misc]

    def test_unique_event_ids(self) -> None:
        e1 = EventEnvelope.build(
            event_type=EventType.CREATED,
            entity_type="Process",
            entity_gid="123",
            source="test",
        )
        e2 = EventEnvelope.build(
            event_type=EventType.CREATED,
            entity_type="Process",
            entity_gid="123",
            source="test",
        )
        assert e1.event_id != e2.event_id
