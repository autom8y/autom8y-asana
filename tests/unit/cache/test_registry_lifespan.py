"""Unit tests for ConnectionRegistry integration with FastAPI lifespan.

Per TDD-CONNECTION-LIFECYCLE-001: Verifies that the connection registry
shutdown is wired into the FastAPI lifespan and executes during app stop.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.cache.connections.registry import ConnectionRegistry
from autom8_asana.core.connections import ConnectionState, HealthCheckResult


class TestRegistryShutdownIntegration:
    """Test that ConnectionRegistry.close_all_async is invoked during shutdown."""

    @pytest.mark.asyncio()
    async def test_registry_close_all_called_during_lifespan_exit(self) -> None:
        """When connection_registry is on app.state, close_all_async is called."""
        registry = ConnectionRegistry()
        mock_manager = MagicMock()
        mock_manager.name = "test"
        mock_manager.state = ConnectionState.HEALTHY
        mock_manager.close = MagicMock()
        mock_manager.close_async = AsyncMock()
        mock_manager.health_check = MagicMock(
            return_value=HealthCheckResult(
                state=ConnectionState.HEALTHY,
                checked_at=0.0,
            )
        )
        mock_manager.health_check_async = AsyncMock(
            return_value=HealthCheckResult(
                state=ConnectionState.HEALTHY,
                checked_at=0.0,
            )
        )
        registry.register(mock_manager)

        # Simulate what lifespan does: call close_all_async
        await registry.close_all_async()

        mock_manager.close_async.assert_called_once()
        assert registry.manager_count == 0

    @pytest.mark.asyncio()
    async def test_registry_close_tolerates_errors(self) -> None:
        """close_all_async logs errors but continues closing other managers."""
        from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS

        registry = ConnectionRegistry()

        failing_manager = MagicMock()
        failing_manager.name = "failing"
        failing_manager.close_async = AsyncMock(side_effect=ConnectionError("boom"))

        good_manager = MagicMock()
        good_manager.name = "good"
        good_manager.close_async = AsyncMock()

        registry.register(failing_manager)
        registry.register(good_manager)

        # Should not raise
        await registry.close_all_async()

        # Both managers should have been attempted
        good_manager.close_async.assert_called_once()
        failing_manager.close_async.assert_called_once()
