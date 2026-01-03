"""Protocol definitions for autom8y-telemetry POC.

This is prototype code - demonstrates interface contracts only.
Production version would live in autom8y_telemetry package.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RateLimiterProtocol(Protocol):
    """Protocol for rate limiting implementations.

    Defines the contract that any rate limiter must implement
    to be compatible with instrumented HTTP clients.
    """

    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens from the rate limiter.

        Blocks until the requested number of tokens are available.

        Args:
            tokens: Number of tokens to acquire (default: 1)
        """
        ...

    @property
    def available_tokens(self) -> float:
        """Get current available tokens (approximate)."""
        ...

    def get_stats(self) -> dict[str, Any]:
        """Get rate limiter statistics for monitoring."""
        ...


@runtime_checkable
class TelemetryHookProtocol(Protocol):
    """Protocol for telemetry hooks.

    Allows injecting custom observability logic into HTTP requests
    without tight coupling to specific telemetry backends.
    """

    async def on_request_start(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """Called before HTTP request starts.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            headers: Request headers (may be modified)

        Returns:
            Context dict to pass to on_request_end
        """
        ...

    async def on_request_end(
        self,
        context: dict[str, Any],
        status_code: int,
        duration_ms: float,
        error: Exception | None = None,
    ) -> None:
        """Called after HTTP request completes.

        Args:
            context: Context dict from on_request_start
            status_code: HTTP status code (or 0 if failed before response)
            duration_ms: Request duration in milliseconds
            error: Exception if request failed
        """
        ...


@runtime_checkable
class LogProviderProtocol(Protocol):
    """Protocol for logging providers.

    Minimal logging interface for POC demonstration.
    Production version would include full LogProvider from autom8_asana.
    """

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message."""
        ...

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log info message."""
        ...

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message."""
        ...

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log error message."""
        ...
