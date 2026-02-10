"""Tests for EventRoutingConfig.

Per GAP-03 FR-005: Declarative subscription configuration.
Per ADR-GAP03-005: EVENTS_ENABLED feature flag.
"""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from autom8_asana.automation.events.config import EventRoutingConfig, SubscriptionEntry


class TestSubscriptionMatching:
    """Test SubscriptionEntry.matches()."""

    def test_wildcard_matches_all(self) -> None:
        sub = SubscriptionEntry(destination="test://queue")
        assert sub.matches("created", "Process") is True
        assert sub.matches("updated", "Offer") is True
        assert sub.matches("section_changed", "Task") is True

    def test_event_type_filter(self) -> None:
        sub = SubscriptionEntry(
            event_types=["section_changed"],
            destination="test://queue",
        )
        assert sub.matches("section_changed", "Process") is True
        assert sub.matches("created", "Process") is False

    def test_entity_type_filter(self) -> None:
        sub = SubscriptionEntry(
            entity_types=["Process"],
            destination="test://queue",
        )
        assert sub.matches("created", "Process") is True
        assert sub.matches("created", "Offer") is False

    def test_combined_filters(self) -> None:
        sub = SubscriptionEntry(
            event_types=["section_changed"],
            entity_types=["Process"],
            destination="test://queue",
        )
        assert sub.matches("section_changed", "Process") is True
        assert sub.matches("section_changed", "Offer") is False
        assert sub.matches("created", "Process") is False

    def test_multiple_event_types(self) -> None:
        sub = SubscriptionEntry(
            event_types=["created", "updated"],
            destination="test://queue",
        )
        assert sub.matches("created", "Process") is True
        assert sub.matches("updated", "Process") is True
        assert sub.matches("deleted", "Process") is False


class TestEventRoutingConfig:
    """Test EventRoutingConfig.matching_subscriptions()."""

    def test_disabled_returns_empty(self) -> None:
        config = EventRoutingConfig(
            enabled=False,
            subscriptions=[SubscriptionEntry(destination="test://q")],
        )
        result = config.matching_subscriptions("created", "Process")
        assert result == []

    def test_enabled_returns_matching(self) -> None:
        config = EventRoutingConfig(
            enabled=True,
            subscriptions=[SubscriptionEntry(destination="test://q")],
        )
        result = config.matching_subscriptions("created", "Process")
        assert len(result) == 1

    def test_multiple_matching_subscriptions(self) -> None:
        config = EventRoutingConfig(
            enabled=True,
            subscriptions=[
                SubscriptionEntry(destination="dest-a"),
                SubscriptionEntry(
                    event_types=["created"],
                    destination="dest-b",
                ),
            ],
        )
        result = config.matching_subscriptions("created", "Process")
        assert len(result) == 2

    def test_partial_match(self) -> None:
        config = EventRoutingConfig(
            enabled=True,
            subscriptions=[
                SubscriptionEntry(
                    event_types=["created"],
                    destination="dest-a",
                ),
                SubscriptionEntry(
                    event_types=["deleted"],
                    destination="dest-b",
                ),
            ],
        )
        result = config.matching_subscriptions("created", "Process")
        assert len(result) == 1
        assert result[0].destination == "dest-a"


class TestEventRoutingConfigFromEnv:
    """Test EventRoutingConfig.from_env()."""

    def test_default_disabled(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = EventRoutingConfig.from_env()
        assert config.enabled is False
        assert config.subscriptions == []

    def test_simple_mode_queue_url(self) -> None:
        env = {
            "EVENTS_ENABLED": "true",
            "EVENTS_SQS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123/asana-events",
        }
        with patch.dict(os.environ, env, clear=True):
            config = EventRoutingConfig.from_env()

        assert config.enabled is True
        assert len(config.subscriptions) == 1
        sub = config.subscriptions[0]
        assert sub.destination == "https://sqs.us-east-1.amazonaws.com/123/asana-events"
        assert sub.event_types == []  # wildcard
        assert sub.entity_types == []  # wildcard

    def test_advanced_mode_subscriptions_json(self) -> None:
        subs = [
            {
                "event_types": ["section_changed"],
                "entity_types": ["Process"],
                "destination": "https://sqs.example.com/pipeline-events",
            },
            {
                "destination": "https://sqs.example.com/all-events",
            },
        ]
        env = {
            "EVENTS_ENABLED": "true",
            "EVENTS_SUBSCRIPTIONS": json.dumps(subs),
        }
        with patch.dict(os.environ, env, clear=True):
            config = EventRoutingConfig.from_env()

        assert config.enabled is True
        assert len(config.subscriptions) == 2
        assert config.subscriptions[0].event_types == ["section_changed"]
        assert config.subscriptions[0].entity_types == ["Process"]
        assert config.subscriptions[1].event_types == []

    def test_enabled_no_destination_raises(self) -> None:
        env = {"EVENTS_ENABLED": "true"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="no destination configured"):
                EventRoutingConfig.from_env()

    def test_disabled_with_queue_url_no_error(self) -> None:
        env = {
            "EVENTS_ENABLED": "false",
            "EVENTS_SQS_QUEUE_URL": "https://sqs.example.com/queue",
        }
        with patch.dict(os.environ, env, clear=True):
            config = EventRoutingConfig.from_env()

        assert config.enabled is False
        assert len(config.subscriptions) == 1

    def test_malformed_subscriptions_json_raises(self) -> None:
        """Invalid JSON in EVENTS_SUBSCRIPTIONS raises ValueError."""
        env = {
            "EVENTS_ENABLED": "true",
            "EVENTS_SUBSCRIPTIONS": "not-valid-json",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError):
                EventRoutingConfig.from_env()

    def test_subscription_missing_destination_raises(self) -> None:
        """Subscription entry without destination raises ValueError."""
        env = {
            "EVENTS_ENABLED": "true",
            "EVENTS_SUBSCRIPTIONS": json.dumps([{"event_types": ["created"]}]),
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="missing required.*destination"):
                EventRoutingConfig.from_env()

    def test_subscriptions_json_takes_precedence(self) -> None:
        """EVENTS_SUBSCRIPTIONS takes precedence over EVENTS_SQS_QUEUE_URL."""
        env = {
            "EVENTS_ENABLED": "true",
            "EVENTS_SQS_QUEUE_URL": "https://sqs.example.com/ignored",
            "EVENTS_SUBSCRIPTIONS": json.dumps(
                [{"destination": "https://sqs.example.com/used"}]
            ),
        }
        with patch.dict(os.environ, env, clear=True):
            config = EventRoutingConfig.from_env()

        assert len(config.subscriptions) == 1
        assert config.subscriptions[0].destination == "https://sqs.example.com/used"
