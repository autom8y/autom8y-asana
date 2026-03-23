"""Tests for DataServiceClient.is_healthy() method.

Per TDD sprint-2 Item 1: Public health check interface that delegates
to the circuit breaker without wrapping or swallowing exceptions.

Per ADR-bridge-validate-extraction Decision 1.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from autom8y_http import CircuitBreakerOpenError as SdkCBOpen

from autom8_asana.clients.data.client import DataServiceClient


class TestIsHealthy:
    """Tests for DataServiceClient.is_healthy()."""

    @pytest.mark.asyncio
    async def test_is_healthy_when_circuit_breaker_closed(self) -> None:
        """is_healthy() completes without raising when circuit breaker is closed."""
        client = DataServiceClient()
        client._circuit_breaker.check = AsyncMock(return_value=None)

        # Should not raise
        await client.is_healthy()

        client._circuit_breaker.check.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_is_healthy_raises_when_circuit_breaker_open(self) -> None:
        """is_healthy() propagates CircuitBreakerOpenError unchanged."""
        client = DataServiceClient()
        original_error = SdkCBOpen(5.0, "Circuit breaker is open")
        client._circuit_breaker.check = AsyncMock(side_effect=original_error)

        with pytest.raises(SdkCBOpen) as exc_info:
            await client.is_healthy()

        # Same instance, not wrapped
        assert exc_info.value is original_error

    @pytest.mark.asyncio
    async def test_is_healthy_raises_when_half_open_fails(self) -> None:
        """is_healthy() propagates exception from half-open state check."""
        client = DataServiceClient()
        half_open_error = SdkCBOpen(2.0, "Half-open probe failed")
        client._circuit_breaker.check = AsyncMock(side_effect=half_open_error)

        with pytest.raises(SdkCBOpen) as exc_info:
            await client.is_healthy()

        assert exc_info.value is half_open_error
        assert "Half-open" in str(exc_info.value)
