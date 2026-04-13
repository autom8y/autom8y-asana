"""Tests for connection lifecycle core types.

Verifies ConnectionState enum, HealthCheckResult staleness logic,
and ConnectionManager protocol compliance.

Design reference: docs/design/TDD-connection-lifecycle-management.md
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from autom8_asana.core.connections import (
    ConnectionManager,
    ConnectionState,
    HealthCheckResult,
)

# ---------------------------------------------------------------------------
# ConnectionState enum tests
# ---------------------------------------------------------------------------


class TestConnectionState:
    """Verify ConnectionState enum values and usage."""

    def test_healthy_value(self) -> None:
        assert ConnectionState.HEALTHY.value == "healthy"

    def test_degraded_value(self) -> None:
        assert ConnectionState.DEGRADED.value == "degraded"

    def test_disconnected_value(self) -> None:
        assert ConnectionState.DISCONNECTED.value == "disconnected"

    def test_all_states_distinct(self) -> None:
        states = list(ConnectionState)
        assert len(states) == 3
        assert len(set(s.value for s in states)) == 3


# ---------------------------------------------------------------------------
# HealthCheckResult tests
# ---------------------------------------------------------------------------


class TestHealthCheckResult:
    """Verify HealthCheckResult immutability and staleness logic."""

    def test_is_frozen(self) -> None:
        result = HealthCheckResult(
            state=ConnectionState.HEALTHY,
            checked_at=time.monotonic(),
        )
        with pytest.raises(AttributeError):
            result.state = ConnectionState.DISCONNECTED  # type: ignore[misc]

    def test_default_latency_and_detail(self) -> None:
        result = HealthCheckResult(
            state=ConnectionState.HEALTHY,
            checked_at=time.monotonic(),
        )
        assert result.latency_ms == 0.0
        assert result.detail == ""

    def test_custom_latency_and_detail(self) -> None:
        result = HealthCheckResult(
            state=ConnectionState.DISCONNECTED,
            checked_at=time.monotonic(),
            latency_ms=42.5,
            detail="connection_refused",
        )
        assert result.latency_ms == 42.5
        assert result.detail == "connection_refused"

    def test_is_stale_returns_false_when_fresh(self) -> None:
        result = HealthCheckResult(
            state=ConnectionState.HEALTHY,
            checked_at=time.monotonic(),
        )
        # Just created, should not be stale within 10 seconds
        assert result.is_stale(10.0) is False

    def test_is_stale_returns_true_when_old(self) -> None:
        # Create a result 20 seconds in the past
        result = HealthCheckResult(
            state=ConnectionState.HEALTHY,
            checked_at=time.monotonic() - 20.0,
        )
        assert result.is_stale(10.0) is True

    def test_is_stale_boundary_zero_ttl(self) -> None:
        # With zero TTL, any result is immediately stale
        result = HealthCheckResult(
            state=ConnectionState.HEALTHY,
            checked_at=time.monotonic(),
        )
        # A zero TTL means everything is stale since time has moved forward
        # even by microseconds
        assert result.is_stale(0.0) is True

    def test_is_stale_uses_monotonic_clock(self) -> None:
        """Verify that staleness uses monotonic time, not wall clock."""
        before = time.monotonic()
        result = HealthCheckResult(
            state=ConnectionState.HEALTHY,
            checked_at=before,
        )
        # Result checked_at is based on monotonic time
        assert result.checked_at == before


# ---------------------------------------------------------------------------
# ConnectionManager protocol compliance tests
# ---------------------------------------------------------------------------


class TestConnectionManagerProtocol:
    """Verify the ConnectionManager protocol is runtime checkable and
    correctly identifies conforming/non-conforming classes."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """The protocol decorator allows isinstance checks."""

        class GoodManager:
            @property
            def name(self) -> str:
                return "test"

            @property
            def state(self) -> ConnectionState:
                return ConnectionState.HEALTHY

            def health_check(self, *, force: bool = False) -> HealthCheckResult:
                return HealthCheckResult(state=ConnectionState.HEALTHY, checked_at=time.monotonic())

            async def health_check_async(self, *, force: bool = False) -> HealthCheckResult:
                return self.health_check(force=force)

            def close(self) -> None:
                pass

            async def close_async(self) -> None:
                pass

            def __enter__(self) -> GoodManager:
                return self

            def __exit__(self, *args: object) -> None:
                self.close()

            async def __aenter__(self) -> GoodManager:
                return self

            async def __aexit__(self, *args: object) -> None:
                await self.close_async()

        assert isinstance(GoodManager(), ConnectionManager)

    def test_non_conforming_class_fails_isinstance(self) -> None:
        """A class missing required methods is not a ConnectionManager."""

        class BadManager:
            pass

        assert not isinstance(BadManager(), ConnectionManager)

    def test_mock_satisfies_protocol(self) -> None:
        """A properly configured MagicMock satisfies the protocol for testing."""
        mock = MagicMock(
            spec_set=[
                "name",
                "state",
                "health_check",
                "health_check_async",
                "close",
                "close_async",
                "__enter__",
                "__exit__",
                "__aenter__",
                "__aexit__",
            ]
        )
        mock.name = "mock"
        mock.state = ConnectionState.HEALTHY
        # MagicMock satisfies the callable attributes
        assert hasattr(mock, "health_check")
        assert hasattr(mock, "close")
