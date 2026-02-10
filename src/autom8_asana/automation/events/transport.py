"""Transport abstraction for event publication.

Per GAP-03 FR-004: Pluggable transport backend.
Per ADR-GAP03-004: SQS direct transport via boto3.
Per NFR-003: InMemoryTransport for unit testing without external dependencies.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Protocol

from autom8_asana.automation.events.envelope import EventEnvelope


class EventTransport(Protocol):
    """Transport interface for event publication.

    Implementations must handle their own error logging.
    """

    async def publish(self, envelope: EventEnvelope, destination: str) -> None:
        """Publish a single event envelope to a destination.

        Args:
            envelope: The event to publish.
            destination: Transport-specific destination (queue URL, topic ARN, etc.).

        Raises:
            Exception: Transport errors are expected to be caught by the caller.
        """
        ...


class InMemoryTransport:
    """In-memory transport for unit testing.

    Per NFR-003: Substitutable test double with no external dependencies.
    """

    def __init__(self) -> None:
        self.published: list[tuple[EventEnvelope, str]] = []

    async def publish(self, envelope: EventEnvelope, destination: str) -> None:
        """Store envelope in memory."""
        self.published.append((envelope, destination))

    def clear(self) -> None:
        """Clear all stored envelopes."""
        self.published.clear()

    @property
    def count(self) -> int:
        """Number of published envelopes."""
        return len(self.published)

    def get_envelopes(self, event_type: str | None = None) -> list[EventEnvelope]:
        """Get published envelopes, optionally filtered by event type.

        Args:
            event_type: Optional filter by event type value.

        Returns:
            List of matching envelopes.
        """
        if event_type is None:
            return [env for env, _ in self.published]
        return [env for env, _ in self.published if env.event_type.value == event_type]


class SQSTransport:
    """AWS SQS transport implementation.

    Per ADR-GAP03-004: Direct boto3, following platform conventions.
    Uses asyncio.to_thread() for the blocking boto3 call.
    """

    def __init__(self, sqs_client: Any) -> None:
        """Initialize with boto3 SQS client.

        Args:
            sqs_client: boto3 SQS client (injected for testability).
        """
        self._sqs = sqs_client

    async def publish(self, envelope: EventEnvelope, destination: str) -> None:
        """Publish envelope to SQS queue.

        Args:
            envelope: Event to publish.
            destination: SQS queue URL.
        """
        message_body = json.dumps(envelope.to_json_dict())

        await asyncio.to_thread(
            self._sqs.send_message,
            QueueUrl=destination,
            MessageBody=message_body,
            MessageAttributes={
                "event_type": {
                    "DataType": "String",
                    "StringValue": envelope.event_type.value,
                },
                "entity_type": {
                    "DataType": "String",
                    "StringValue": envelope.entity_type,
                },
                "schema_version": {
                    "DataType": "String",
                    "StringValue": envelope.schema_version,
                },
            },
        )

    @classmethod
    def from_boto3(cls, **kwargs: Any) -> SQSTransport:
        """Create SQSTransport with default boto3 client.

        Args:
            **kwargs: Passed to boto3.client() (e.g., endpoint_url for LocalStack).

        Returns:
            SQSTransport with SQS client.
        """
        import boto3

        return cls(sqs_client=boto3.client("sqs", **kwargs))
