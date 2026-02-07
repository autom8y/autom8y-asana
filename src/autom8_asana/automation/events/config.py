"""Event routing configuration.

Per GAP-03 FR-005: Declarative subscription configuration.
Per ADR-GAP03-005: EVENTS_ENABLED feature flag.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SubscriptionEntry:
    """A single subscription mapping events to a destination.

    Attributes:
        event_types: List of event type values to match (empty = match all).
        entity_types: List of entity type names to match (empty = match all).
        destination: Transport-specific destination (e.g., SQS queue URL).
    """

    event_types: list[str] = field(default_factory=list)
    entity_types: list[str] = field(default_factory=list)
    destination: str = ""

    def matches(self, event_type: str, entity_type: str) -> bool:
        """Check if this subscription matches the given event.

        Args:
            event_type: Event type value (e.g., "created").
            entity_type: Entity type name (e.g., "Process").

        Returns:
            True if subscription matches (empty filter = wildcard).
        """
        if self.event_types and event_type not in self.event_types:
            return False
        if self.entity_types and entity_type not in self.entity_types:
            return False
        return True


@dataclass
class EventRoutingConfig:
    """Configuration for event routing.

    Per FR-005/NFR-004: Declarative, configurable subscriptions.
    Per ADR-GAP03-005: EVENTS_ENABLED feature flag.
    """

    enabled: bool = False
    subscriptions: list[SubscriptionEntry] = field(default_factory=list)

    def matching_subscriptions(
        self, event_type: str, entity_type: str
    ) -> list[SubscriptionEntry]:
        """Find all subscriptions matching the given event.

        Args:
            event_type: Event type value.
            entity_type: Entity type name.

        Returns:
            List of matching subscriptions. Empty if disabled.
        """
        if not self.enabled:
            return []
        return [s for s in self.subscriptions if s.matches(event_type, entity_type)]

    @classmethod
    def from_env(cls) -> EventRoutingConfig:
        """Load configuration from environment variables.

        Environment variables:
            EVENTS_ENABLED: "true" or "false" (default "false")
            EVENTS_SQS_QUEUE_URL: SQS queue URL for default subscription
            EVENTS_SUBSCRIPTIONS: JSON array of subscription objects (advanced)

        Returns:
            EventRoutingConfig instance.

        Raises:
            ValueError: If EVENTS_ENABLED=true but no destination configured.
        """
        enabled = os.environ.get("EVENTS_ENABLED", "false").lower() == "true"
        queue_url = os.environ.get("EVENTS_SQS_QUEUE_URL", "")
        subscriptions_json = os.environ.get("EVENTS_SUBSCRIPTIONS", "")

        subscriptions: list[SubscriptionEntry] = []

        # Advanced: explicit subscription list
        if subscriptions_json:
            raw = json.loads(subscriptions_json)
            for entry in raw:
                subscriptions.append(
                    SubscriptionEntry(
                        event_types=entry.get("event_types", []),
                        entity_types=entry.get("entity_types", []),
                        destination=entry["destination"],
                    )
                )

        # Simple: single queue URL creates wildcard subscription
        elif queue_url:
            subscriptions.append(SubscriptionEntry(destination=queue_url))

        # Startup validation: enabled but no destination
        if enabled and not subscriptions:
            raise ValueError(
                "EVENTS_ENABLED=true but no destination configured. "
                "Set EVENTS_SQS_QUEUE_URL or EVENTS_SUBSCRIPTIONS."
            )

        return cls(enabled=enabled, subscriptions=subscriptions)
