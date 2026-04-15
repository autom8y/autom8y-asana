"""Tests for SQSTransport.

Per GAP-03 SC-005: SQS transport works end-to-end.
Unit tests use mocked boto3 client.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from autom8_asana.automation.events.envelope import EventEnvelope
from autom8_asana.automation.events.transport import SQSTransport
from autom8_asana.automation.events.types import EventType


def _make_envelope(
    event_type: EventType = EventType.SECTION_CHANGED,
) -> EventEnvelope:
    return EventEnvelope.build(
        event_type=event_type,
        entity_type="Process",
        entity_gid="1234567890",
        source="save_session",
        payload={"process_type": "sales"},
    )


class TestSQSTransport:
    """Test SQSTransport with mocked boto3 client."""

    async def test_publish_calls_send_message(self) -> None:
        sqs_client = MagicMock()
        transport = SQSTransport(sqs_client=sqs_client)
        envelope = _make_envelope()
        queue_url = "https://sqs.us-east-1.amazonaws.com/123/asana-events"

        await transport.publish(envelope, queue_url)

        sqs_client.send_message.assert_called_once()
        call_kwargs = sqs_client.send_message.call_args
        assert call_kwargs.kwargs["QueueUrl"] == queue_url

    async def test_message_body_is_json_envelope(self) -> None:
        sqs_client = MagicMock()
        transport = SQSTransport(sqs_client=sqs_client)
        envelope = _make_envelope()

        await transport.publish(envelope, "https://sqs.example.com/queue")

        call_kwargs = sqs_client.send_message.call_args
        body = json.loads(call_kwargs.kwargs["MessageBody"])
        assert body["event_type"] == "section_changed"
        assert body["entity_type"] == "Process"
        assert body["entity_gid"] == "1234567890"
        assert body["payload"]["process_type"] == "sales"

    async def test_message_attributes_set(self) -> None:
        sqs_client = MagicMock()
        transport = SQSTransport(sqs_client=sqs_client)
        envelope = _make_envelope()

        await transport.publish(envelope, "https://sqs.example.com/queue")

        call_kwargs = sqs_client.send_message.call_args
        attrs = call_kwargs.kwargs["MessageAttributes"]
        assert attrs["event_type"]["StringValue"] == "section_changed"
        assert attrs["entity_type"]["StringValue"] == "Process"
        assert attrs["schema_version"]["StringValue"] == "1.0"

    async def test_publish_propagates_transport_error(self) -> None:
        sqs_client = MagicMock()
        sqs_client.send_message.side_effect = ConnectionError("SQS unreachable")
        transport = SQSTransport(sqs_client=sqs_client)
        envelope = _make_envelope()

        with pytest.raises(ConnectionError, match="SQS unreachable"):
            await transport.publish(envelope, "https://sqs.example.com/queue")
