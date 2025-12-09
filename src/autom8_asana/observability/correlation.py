"""Correlation ID generation and context for request tracing.

Per TDD-0007 and ADR-0013: SDK generates correlation IDs with format
`sdk-{timestamp_hex}-{random_hex}` for tracing operations.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass


def generate_correlation_id() -> str:
    """Generate SDK correlation ID: sdk-{timestamp_hex}-{random_hex}.

    Format components:
    - `sdk-` prefix: Distinguishes SDK-generated IDs from Asana's X-Request-Id
    - `timestamp_hex`: 8 hex chars, lower 32 bits of Unix timestamp (milliseconds)
    - `random_hex`: 4 hex chars, random component for uniqueness

    Returns:
        Correlation ID string (18 characters), e.g., "sdk-192f3a1b-4c7e"
    """
    # Lower 32 bits of millisecond timestamp
    timestamp = int(time.time() * 1000) & 0xFFFFFFFF
    # 4 hex characters of randomness (2 bytes)
    random_part = secrets.token_hex(2)
    return f"sdk-{timestamp:08x}-{random_part}"


@dataclass(frozen=True)
class CorrelationContext:
    """Immutable context for a single SDK operation.

    Per TDD-0007, this captures all correlation information for an operation,
    enabling consistent logging and exception enrichment.

    Attributes:
        correlation_id: SDK-generated correlation ID for this operation.
        operation: Operation name, e.g., 'TasksClient.get_async'.
        started_at: Unix timestamp when operation started.
        resource_gid: Optional GID of the resource being operated on.
        asana_request_id: X-Request-Id from Asana response (set after request completes).
    """

    correlation_id: str
    operation: str
    started_at: float
    resource_gid: str | None = None
    asana_request_id: str | None = None

    @staticmethod
    def generate(
        operation: str,
        resource_gid: str | None = None,
    ) -> CorrelationContext:
        """Create new context with fresh correlation ID.

        Args:
            operation: Operation name, e.g., 'TasksClient.get_async'.
            resource_gid: Optional GID of the resource being operated on.

        Returns:
            New CorrelationContext with generated correlation ID.
        """
        return CorrelationContext(
            correlation_id=generate_correlation_id(),
            operation=operation,
            started_at=time.monotonic(),
            resource_gid=resource_gid,
        )

    def with_asana_request_id(self, request_id: str) -> CorrelationContext:
        """Return new context with Asana request ID set.

        Args:
            request_id: X-Request-Id from Asana response.

        Returns:
            New CorrelationContext with asana_request_id set.
        """
        return CorrelationContext(
            correlation_id=self.correlation_id,
            operation=self.operation,
            started_at=self.started_at,
            resource_gid=self.resource_gid,
            asana_request_id=request_id,
        )

    def format_log_prefix(self) -> str:
        """Format prefix for log messages.

        Returns:
            Log prefix string, e.g., '[sdk-192f3a1b-4c7e]'.
        """
        return f"[{self.correlation_id}]"

    def format_operation(self) -> str:
        """Format operation with optional resource GID.

        Returns:
            Formatted operation string, e.g., 'TasksClient.get_async(123)'.
        """
        if self.resource_gid:
            return f"{self.operation}({self.resource_gid})"
        return f"{self.operation}()"
