"""Connection lifecycle management for cache backends.

Provides the ConnectionManager protocol, ConnectionState enum, and
HealthCheckResult dataclass for unified connection lifecycle management
across Redis and S3 backends.

Components:
- ConnectionState: Enum for connection health states (healthy/degraded/disconnected)
- HealthCheckResult: Cached result of a health check probe with staleness check
- ConnectionManager: Protocol that all connection-backed resources implement

Module: src/autom8_asana/core/connections.py

Design reference: docs/design/TDD-connection-lifecycle-management.md
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


class ConnectionState(enum.Enum):
    """Connection health states reported by ConnectionManagers.

    Values:
        HEALTHY: Backend is responsive and accepting operations.
        DEGRADED: Backend is partially available or recovering (e.g., circuit half-open).
        DISCONNECTED: Backend is unavailable (closed, circuit open, or unreachable).
    """

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"


@dataclass(frozen=True)
class HealthCheckResult:
    """Cached result of a health check probe.

    Immutable snapshot of a health check at a specific point in time.
    Used by ConnectionManagers to avoid redundant I/O on rapid health probes.

    Attributes:
        state: Current connection state at time of check.
        checked_at: Monotonic timestamp when check was performed.
        latency_ms: Probe latency in milliseconds (0.0 if not measured).
        detail: Optional human-readable detail string for diagnostics.
    """

    state: ConnectionState
    checked_at: float  # time.monotonic()
    latency_ms: float = 0.0
    detail: str = ""

    def is_stale(self, max_age_seconds: float) -> bool:
        """Check if this result is older than max_age_seconds.

        Args:
            max_age_seconds: Maximum age in seconds before result is stale.

        Returns:
            True if the result is older than max_age_seconds.
        """
        return (time.monotonic() - self.checked_at) > max_age_seconds


@runtime_checkable
class ConnectionManager(Protocol):
    """Protocol for backend connection lifecycle management.

    Implementations own the creation, health monitoring, and shutdown
    of connections to a specific backend (Redis, S3, etc.).

    ConnectionManagers are long-lived objects (application singleton scope).
    They are created during app startup and closed during shutdown.

    Contract:
    - ``name`` returns a stable string unique within a registry.
    - ``state`` returns ConnectionState without performing I/O.
    - ``health_check()`` returns HealthCheckResult with I/O only when cache is stale.
    - ``close()`` is idempotent; calling it multiple times is safe.
    - After ``close()``, ``state`` returns DISCONNECTED.
    - Both sync and async variants are provided for dual-mode callers.
    """

    @property
    def name(self) -> str:
        """Unique identifier for this connection manager (e.g., 'redis', 's3')."""
        ...

    @property
    def state(self) -> ConnectionState:
        """Current connection state. Uses cached health check if available."""
        ...

    def health_check(self, *, force: bool = False) -> HealthCheckResult:
        """Perform a health check, returning a cached result if fresh.

        Args:
            force: If True, bypass cache and perform a live probe.

        Returns:
            HealthCheckResult with current state and latency.
        """
        ...

    async def health_check_async(self, *, force: bool = False) -> HealthCheckResult:
        """Async variant of health_check for async callers.

        Args:
            force: If True, bypass cache and perform a live probe.

        Returns:
            HealthCheckResult with current state and latency.
        """
        ...

    def close(self) -> None:
        """Release all resources held by this manager.

        After close(), the manager is in DISCONNECTED state.
        Calling close() multiple times is safe (idempotent).
        """
        ...

    async def close_async(self) -> None:
        """Async variant of close for async callers."""
        ...

    def __enter__(self) -> ConnectionManager:
        """Sync context manager entry."""
        ...

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Sync context manager exit -- calls close()."""
        ...

    async def __aenter__(self) -> ConnectionManager:
        """Async context manager entry."""
        ...

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit -- calls close_async()."""
        ...
