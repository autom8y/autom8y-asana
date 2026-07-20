"""Integration tests for SQS transport with LocalStack.

Per GAP-03 SC-005: One concrete transport works end-to-end.
Requires: docker-compose up -d (LocalStack with SQS enabled).

These tests are skipped if LocalStack is not running.
"""

from __future__ import annotations

import contextlib
import json

import pytest

from autom8_asana.automation.events.envelope import EventEnvelope
from autom8_asana.automation.events.transport import SQSTransport
from autom8_asana.automation.events.types import EventType

LOCALSTACK_ENDPOINT = "http://localhost:4566"
QUEUE_NAME = "asana-events-test"


def _localstack_available() -> bool:
    try:
        import boto3

        client = boto3.client(
            "sqs",
            endpoint_url=LOCALSTACK_ENDPOINT,
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        client.list_queues()
        return True
    except Exception:  # noqa: BLE001
        return False


localstack_required = pytest.mark.skipif(
    not _localstack_available(),
    reason="LocalStack not running (docker-compose up -d)",
)


@pytest.fixture
def sqs_queue() -> str:
    """Create a test SQS queue and return its URL."""
    import boto3

    client = boto3.client(
        "sqs",
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )

    # Create queue (idempotent)
    response = client.create_queue(QueueName=QUEUE_NAME)
    queue_url = response["QueueUrl"]

    # Purge any leftover messages
    with contextlib.suppress(client.exceptions.PurgeQueueInProgress):
        client.purge_queue(QueueUrl=queue_url)

    yield queue_url

    # Cleanup
    with contextlib.suppress(Exception):
        client.delete_queue(QueueUrl=queue_url)


@pytest.fixture
def sqs_transport() -> SQSTransport:
    """Create SQSTransport pointed at LocalStack."""
    return SQSTransport.from_boto3(
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


@pytest.fixture
def sqs_client():
    """Raw boto3 SQS client for reading messages."""
    import boto3

    return boto3.client(
        "sqs",
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


@localstack_required
class TestSQSIntegration:
    """Integration tests with real SQS (via LocalStack)."""

    async def test_publish_and_receive(
        self,
        sqs_transport: SQSTransport,
        sqs_queue: str,
        sqs_client,
    ) -> None:
        """SC-005: Message arrives in SQS queue."""
        envelope = EventEnvelope.build(
            event_type=EventType.SECTION_CHANGED,
            entity_type="Process",
            entity_gid="1234567890",
            source="save_session",
            payload={"section_gid": "9876543210"},
        )

        await sqs_transport.publish(envelope, sqs_queue)

        # Read message back
        response = sqs_client.receive_message(
            QueueUrl=sqs_queue,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5,
            MessageAttributeNames=["All"],
        )

        messages = response.get("Messages", [])
        assert len(messages) == 1

        body = json.loads(messages[0]["Body"])
        assert body["entity_gid"] == "1234567890"
        assert body["event_type"] == "section_changed"

    async def test_message_attributes(
        self,
        sqs_transport: SQSTransport,
        sqs_queue: str,
        sqs_client,
    ) -> None:
        """Verify SQS message attributes are set correctly."""
        envelope = EventEnvelope.build(
            event_type=EventType.CREATED,
            entity_type="Offer",
            entity_gid="999",
            source="test",
        )

        await sqs_transport.publish(envelope, sqs_queue)

        response = sqs_client.receive_message(
            QueueUrl=sqs_queue,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5,
            MessageAttributeNames=["All"],
        )

        messages = response.get("Messages", [])
        assert len(messages) == 1

        attrs = messages[0].get("MessageAttributes", {})
        assert attrs["event_type"]["StringValue"] == "created"
        assert attrs["entity_type"]["StringValue"] == "Offer"
        assert attrs["schema_version"]["StringValue"] == "1.0"

    async def test_json_body_deserializable(
        self,
        sqs_transport: SQSTransport,
        sqs_queue: str,
        sqs_client,
    ) -> None:
        """Body parses as valid EventEnvelope JSON."""
        envelope = EventEnvelope.build(
            event_type=EventType.UPDATED,
            entity_type="Process",
            entity_gid="555",
            source="save_session",
            correlation_id="test-corr-id",
            payload={"process_type": "sales"},
        )

        await sqs_transport.publish(envelope, sqs_queue)

        response = sqs_client.receive_message(
            QueueUrl=sqs_queue,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5,
        )

        body = json.loads(response["Messages"][0]["Body"])

        # All required envelope fields present
        assert body["schema_version"] == "1.0"
        assert body["event_id"]  # non-empty UUID
        assert body["event_type"] == "updated"
        assert body["entity_type"] == "Process"
        assert body["entity_gid"] == "555"
        assert body["timestamp"]  # non-empty ISO 8601
        assert body["source"] == "save_session"
        assert body["correlation_id"] == "test-corr-id"
        assert body["payload"]["process_type"] == "sales"
