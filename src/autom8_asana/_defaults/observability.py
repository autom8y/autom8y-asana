"""Default no-op observability hook.

Per TDD-HARDENING-A/FR-OBS-010: Default implementation that performs no operations.
"""

from __future__ import annotations


class NullObservabilityHook:
    """No-op observability hook (default).

    Per FR-OBS-010: Default implementation that performs no operations.
    Used when no custom ObservabilityHook is provided to AsanaClient.

    All methods are async no-ops that return immediately without any
    side effects. This ensures zero overhead when observability is not
    configured.

    Example:
        # These are equivalent:
        client = AsanaClient(token="...")
        client = AsanaClient(token="...", observability_hook=NullObservabilityHook())
    """

    async def on_request_start(
        self, method: str, path: str, correlation_id: str
    ) -> None:
        """No-op: called before HTTP request."""
        pass

    async def on_request_end(
        self, method: str, path: str, status: int, duration_ms: float
    ) -> None:
        """No-op: called after HTTP request completes."""
        pass

    async def on_request_error(self, method: str, path: str, error: Exception) -> None:
        """No-op: called on HTTP request error."""
        pass

    async def on_rate_limit(self, retry_after_seconds: int) -> None:
        """No-op: called on rate limit 429."""
        pass

    async def on_circuit_breaker_state_change(
        self, old_state: str, new_state: str
    ) -> None:
        """No-op: called on circuit breaker state change."""
        pass

    async def on_retry(self, attempt: int, max_attempts: int, error: Exception) -> None:
        """No-op: called before retry attempt."""
        pass


__all__ = ["NullObservabilityHook"]
