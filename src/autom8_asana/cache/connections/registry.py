"""Connection registry for coordinated lifecycle management.

Holds references to all ConnectionManager instances and provides
coordinated shutdown (LIFO ordering) and aggregated health reporting.

Module: src/autom8_asana/cache/connections/registry.py

Design reference: docs/design/TDD-connection-lifecycle-management.md
"""

from __future__ import annotations

import time
from threading import Lock

from autom8y_log import get_logger

from autom8_asana.core.connections import (
    ConnectionManager,
    ConnectionState,
    HealthCheckResult,
)
from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS

logger = get_logger(__name__)


class ConnectionRegistry:
    """Registry for coordinated connection lifecycle management.

    Managers are registered during app startup and closed in reverse
    registration order during shutdown (LIFO -- last registered, first closed).
    This ensures dependent services shut down before their dependencies.

    Registration order matters:
    - Register S3 first (cold tier, no dependencies)
    - Register Redis second (hot tier, may read-through from S3)
    - On shutdown: Redis closes first, then S3

    Thread Safety:
        Registration and close are protected by a Lock.
    """

    def __init__(self) -> None:
        self._managers: list[ConnectionManager] = []
        self._lock = Lock()

    def register(self, manager: ConnectionManager) -> None:
        """Register a connection manager for lifecycle coordination.

        Args:
            manager: ConnectionManager to register.
        """
        with self._lock:
            self._managers.append(manager)
            logger.info(
                "connection_manager_registered",
                extra={"name": manager.name},
            )

    def get(self, name: str) -> ConnectionManager | None:
        """Look up a manager by name.

        Args:
            name: Manager identifier (e.g., 'redis', 's3').

        Returns:
            ConnectionManager or None if not found.
        """
        for mgr in self._managers:
            if mgr.name == name:
                return mgr
        return None

    def health_report(self) -> dict[str, HealthCheckResult]:
        """Aggregate health check results from all registered managers.

        Returns:
            Dict mapping manager name to HealthCheckResult.
            Never raises -- errors are captured as DISCONNECTED results.
        """
        report: dict[str, HealthCheckResult] = {}
        for mgr in self._managers:
            try:
                report[mgr.name] = mgr.health_check()
            except CACHE_TRANSIENT_ERRORS as e:
                report[mgr.name] = HealthCheckResult(
                    state=ConnectionState.DISCONNECTED,
                    checked_at=time.monotonic(),
                    detail=str(e),
                )
        return report

    async def health_report_async(self) -> dict[str, HealthCheckResult]:
        """Async health report -- runs checks in parallel.

        Returns:
            Dict mapping manager name to HealthCheckResult.
        """
        import asyncio

        results = await asyncio.gather(
            *[mgr.health_check_async() for mgr in self._managers],
            return_exceptions=True,
        )
        report: dict[str, HealthCheckResult] = {}
        for mgr, result in zip(self._managers, results):
            if isinstance(result, BaseException):
                report[mgr.name] = HealthCheckResult(
                    state=ConnectionState.DISCONNECTED,
                    checked_at=time.monotonic(),
                    detail=str(result),
                )
            else:
                report[mgr.name] = result
        return report

    def close_all(self) -> None:
        """Close all managers in reverse registration order (LIFO).

        Errors during individual manager close are logged and swallowed
        to ensure all managers get a chance to close.
        """
        with self._lock:
            for mgr in reversed(self._managers):
                try:
                    mgr.close()
                except CACHE_TRANSIENT_ERRORS as e:
                    logger.warning(
                        "connection_manager_close_failed",
                        extra={"name": mgr.name, "error": str(e)},
                    )
            self._managers.clear()

    async def close_all_async(self) -> None:
        """Async close -- closes managers sequentially in LIFO order.

        Sequential (not parallel) because shutdown ordering matters
        and we want deterministic cleanup.
        """
        with self._lock:
            for mgr in reversed(self._managers):
                try:
                    await mgr.close_async()
                except CACHE_TRANSIENT_ERRORS as e:
                    logger.warning(
                        "connection_manager_close_failed",
                        extra={"name": mgr.name, "error": str(e)},
                    )
            self._managers.clear()

    @property
    def all_healthy(self) -> bool:
        """True if all registered managers report HEALTHY state."""
        return all(mgr.state == ConnectionState.HEALTHY for mgr in self._managers)

    @property
    def manager_count(self) -> int:
        """Number of registered managers."""
        return len(self._managers)
