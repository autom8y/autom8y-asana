"""Tests for ConnectionRegistry.

Verifies LIFO shutdown ordering, health report aggregation,
close failure tolerance, and empty registry edge cases.

Design reference: docs/design/TDD-connection-lifecycle-management.md
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from autom8_asana.cache.connections.registry import ConnectionRegistry
from autom8_asana.core.connections import ConnectionState, HealthCheckResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_manager(
    name: str,
    state: ConnectionState = ConnectionState.HEALTHY,
) -> MagicMock:
    """Create a mock ConnectionManager with the given name and state."""
    mgr = MagicMock()
    mgr.name = name
    type(mgr).state = PropertyMock(return_value=state)
    mgr.health_check.return_value = HealthCheckResult(
        state=state,
        checked_at=time.monotonic(),
        latency_ms=1.0,
    )
    mgr.health_check_async = AsyncMock(
        return_value=HealthCheckResult(
            state=state,
            checked_at=time.monotonic(),
            latency_ms=1.0,
        )
    )
    mgr.close.return_value = None
    mgr.close_async = AsyncMock(return_value=None)
    return mgr


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistryRegistration:
    """Verify manager registration."""

    def test_register_adds_manager(self) -> None:
        registry = ConnectionRegistry()
        mgr = _make_mock_manager("redis")
        registry.register(mgr)
        assert registry.manager_count == 1

    def test_register_multiple_managers(self) -> None:
        registry = ConnectionRegistry()
        registry.register(_make_mock_manager("s3"))
        registry.register(_make_mock_manager("redis"))
        assert registry.manager_count == 2

    def test_get_by_name(self) -> None:
        registry = ConnectionRegistry()
        redis_mgr = _make_mock_manager("redis")
        s3_mgr = _make_mock_manager("s3")
        registry.register(s3_mgr)
        registry.register(redis_mgr)

        assert registry.get("redis") is redis_mgr
        assert registry.get("s3") is s3_mgr

    def test_get_returns_none_for_unknown(self) -> None:
        registry = ConnectionRegistry()
        assert registry.get("unknown") is None


# ---------------------------------------------------------------------------
# Health report
# ---------------------------------------------------------------------------


class TestRegistryHealthReport:
    """Verify health_report aggregation."""

    def test_health_report_all_healthy(self) -> None:
        registry = ConnectionRegistry()
        registry.register(_make_mock_manager("redis"))
        registry.register(_make_mock_manager("s3"))

        report = registry.health_report()
        assert len(report) == 2
        assert report["redis"].state == ConnectionState.HEALTHY
        assert report["s3"].state == ConnectionState.HEALTHY

    def test_health_report_mixed_states(self) -> None:
        registry = ConnectionRegistry()
        registry.register(_make_mock_manager("redis", ConnectionState.HEALTHY))
        registry.register(_make_mock_manager("s3", ConnectionState.DISCONNECTED))

        report = registry.health_report()
        assert report["redis"].state == ConnectionState.HEALTHY
        assert report["s3"].state == ConnectionState.DISCONNECTED

    def test_health_report_handles_exception(self) -> None:
        """If a manager's health_check raises, it appears as DISCONNECTED."""
        registry = ConnectionRegistry()
        bad_mgr = _make_mock_manager("redis")
        bad_mgr.health_check.side_effect = ConnectionError("probe crashed")
        registry.register(bad_mgr)

        report = registry.health_report()
        assert report["redis"].state == ConnectionState.DISCONNECTED
        assert "probe crashed" in report["redis"].detail

    def test_health_report_empty_registry(self) -> None:
        registry = ConnectionRegistry()
        report = registry.health_report()
        assert report == {}

    def test_health_report_async(self) -> None:
        registry = ConnectionRegistry()
        registry.register(_make_mock_manager("redis"))
        registry.register(_make_mock_manager("s3"))

        report = asyncio.run(registry.health_report_async())
        assert len(report) == 2
        assert report["redis"].state == ConnectionState.HEALTHY

    def test_health_report_async_handles_exception(self) -> None:
        registry = ConnectionRegistry()
        bad_mgr = _make_mock_manager("redis")
        bad_mgr.health_check_async = AsyncMock(
            side_effect=ConnectionError("async probe crashed")
        )
        registry.register(bad_mgr)

        report = asyncio.run(registry.health_report_async())
        assert report["redis"].state == ConnectionState.DISCONNECTED


# ---------------------------------------------------------------------------
# LIFO shutdown ordering
# ---------------------------------------------------------------------------


class TestRegistryLIFOShutdown:
    """Verify managers close in reverse registration order (LIFO)."""

    def test_close_all_lifo_ordering(self) -> None:
        """Register [A, B, C], verify close order is C, B, A."""
        registry = ConnectionRegistry()
        close_order: list[str] = []

        for name in ["A", "B", "C"]:
            mgr = _make_mock_manager(name)
            mgr.close.side_effect = lambda n=name: close_order.append(n)
            registry.register(mgr)

        registry.close_all()
        assert close_order == ["C", "B", "A"]

    def test_close_all_async_lifo_ordering(self) -> None:
        """Async close also uses LIFO ordering."""
        registry = ConnectionRegistry()
        close_order: list[str] = []

        for name in ["A", "B", "C"]:
            mgr = _make_mock_manager(name)

            async def close_async(n: str = name) -> None:
                close_order.append(n)

            mgr.close_async = close_async
            registry.register(mgr)

        asyncio.run(registry.close_all_async())
        assert close_order == ["C", "B", "A"]

    def test_close_all_clears_registry(self) -> None:
        registry = ConnectionRegistry()
        registry.register(_make_mock_manager("redis"))
        registry.register(_make_mock_manager("s3"))
        assert registry.manager_count == 2

        registry.close_all()
        assert registry.manager_count == 0

    def test_close_all_async_clears_registry(self) -> None:
        registry = ConnectionRegistry()
        registry.register(_make_mock_manager("redis"))
        asyncio.run(registry.close_all_async())
        assert registry.manager_count == 0


# ---------------------------------------------------------------------------
# Close failure tolerance
# ---------------------------------------------------------------------------


class TestRegistryCloseFailureTolerance:
    """Verify that close_all continues even if individual managers fail."""

    def test_close_all_tolerates_individual_failure(self) -> None:
        """Register [A, B], make A.close() raise, verify B still closes."""
        registry = ConnectionRegistry()

        mgr_a = _make_mock_manager("A")
        mgr_a.close.side_effect = ConnectionError("A failed to close")

        mgr_b = _make_mock_manager("B")

        registry.register(mgr_a)
        registry.register(mgr_b)

        # Should not raise
        registry.close_all()

        # Both should have been attempted (B first in LIFO)
        mgr_b.close.assert_called_once()
        mgr_a.close.assert_called_once()

    def test_close_all_async_tolerates_individual_failure(self) -> None:
        """Async close also tolerates failures."""
        registry = ConnectionRegistry()

        mgr_a = _make_mock_manager("A")
        mgr_a.close_async = AsyncMock(side_effect=ConnectionError("A failed"))

        mgr_b = _make_mock_manager("B")

        registry.register(mgr_a)
        registry.register(mgr_b)

        asyncio.run(registry.close_all_async())
        # Registry should be cleared even after failures
        assert registry.manager_count == 0


# ---------------------------------------------------------------------------
# all_healthy property
# ---------------------------------------------------------------------------


class TestRegistryAllHealthy:
    """Verify the all_healthy aggregate property."""

    def test_all_healthy_when_all_healthy(self) -> None:
        registry = ConnectionRegistry()
        registry.register(_make_mock_manager("redis", ConnectionState.HEALTHY))
        registry.register(_make_mock_manager("s3", ConnectionState.HEALTHY))
        assert registry.all_healthy is True

    def test_not_all_healthy_when_one_degraded(self) -> None:
        registry = ConnectionRegistry()
        registry.register(_make_mock_manager("redis", ConnectionState.HEALTHY))
        registry.register(_make_mock_manager("s3", ConnectionState.DEGRADED))
        assert registry.all_healthy is False

    def test_not_all_healthy_when_one_disconnected(self) -> None:
        registry = ConnectionRegistry()
        registry.register(_make_mock_manager("redis", ConnectionState.DISCONNECTED))
        assert registry.all_healthy is False

    def test_all_healthy_empty_registry(self) -> None:
        """Empty registry is vacuously healthy (all of zero are healthy)."""
        registry = ConnectionRegistry()
        assert registry.all_healthy is True
