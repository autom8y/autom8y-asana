"""Transport abstraction for event publication.

Per GAP-03 FR-004: Pluggable transport backend.
Per NFR-003: InMemoryTransport for unit testing without external dependencies.
"""

from __future__ import annotations

from typing import Protocol

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
        return [
            env for env, _ in self.published if env.event_type.value == event_type
        ]
