"""Tests for event emission wiring (setup_event_emission).

Per GAP-03 ADR-GAP03-005: EVENTS_ENABLED=false by default.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from autom8_asana.automation.config import AutomationConfig
from autom8_asana.automation.engine import AutomationEngine
from autom8_asana.automation.events import setup_event_emission
from autom8_asana.automation.events.rule import EventEmissionRule


class TestSetupEventEmission:
    """Test setup_event_emission wiring function."""

    def test_disabled_by_default(self) -> None:
        """EVENTS_ENABLED=false by default, no rule registered."""
        engine = AutomationEngine(AutomationConfig())

        with patch.dict(os.environ, {}, clear=True):
            result = setup_event_emission(engine)

        assert result is False
        assert len(engine.rules) == 0

    def test_enabled_with_queue_url(self) -> None:
        """EVENTS_ENABLED=true registers emission rule."""
        engine = AutomationEngine(AutomationConfig())
        env = {
            "EVENTS_ENABLED": "true",
            "EVENTS_SQS_QUEUE_URL": "https://sqs.example.com/queue",
        }

        with patch.dict(os.environ, env, clear=True):
            with patch(
                "autom8_asana.automation.events.SQSTransport.from_boto3"
            ) as mock_transport:
                mock_transport.return_value = mock_transport
                result = setup_event_emission(engine)

        assert result is True
        assert len(engine.rules) == 1
        assert isinstance(engine.rules[0], EventEmissionRule)

    def test_enabled_no_destination_raises(self) -> None:
        """EVENTS_ENABLED=true without destination raises ValueError."""
        engine = AutomationEngine(AutomationConfig())
        env = {"EVENTS_ENABLED": "true"}

        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="no destination configured"):
                setup_event_emission(engine)

    def test_disabled_explicit(self) -> None:
        """EVENTS_ENABLED=false explicitly, no rule registered."""
        engine = AutomationEngine(AutomationConfig())
        env = {"EVENTS_ENABLED": "false"}

        with patch.dict(os.environ, env, clear=True):
            result = setup_event_emission(engine)

        assert result is False
        assert len(engine.rules) == 0
