"""Structured logging context for SDK operations.

Per TDD-HARDENING-A/FR-LOG-002: Provides standard fields for structured logging.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class LogContext:
    """Structured logging context for SDK operations.

    Per FR-LOG-002: Provides standard fields for structured logging.
    All fields are optional; only non-None values are included in output.

    Usage:
        ctx = LogContext(correlation_id="abc123", operation="track")
        logger.info("Processing entity", extra=ctx.to_dict())

    Example:
        # Create context for a tracking operation
        ctx = LogContext(
            correlation_id="req-123",
            operation="track",
            entity_gid="1234567890",
            entity_type="task",
        )
        logger.debug("Tracking entity %s", entity.gid, extra=ctx.to_dict())

        # Create context for a timed operation
        ctx = LogContext(
            correlation_id="req-123",
            operation="commit",
            duration_ms=45.2,
        )
        logger.info("Commit completed", extra=ctx.to_dict())

    Attributes:
        correlation_id: Request correlation ID for distributed tracing.
        operation: Name of the SDK operation (e.g., "track", "commit", "fetch").
        entity_gid: GID of the entity being processed.
        entity_type: Type of entity (e.g., "task", "project", "business").
        duration_ms: Operation duration in milliseconds.
    """

    correlation_id: str | None = None
    operation: str | None = None
    entity_gid: str | None = None
    entity_type: str | None = None
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for logging extra parameter.

        Only includes non-None values to keep log output clean.

        Returns:
            Dict with non-None fields only.

        Example:
            >>> ctx = LogContext(operation="track", entity_gid="123")
            >>> ctx.to_dict()
            {'operation': 'track', 'entity_gid': '123'}
        """
        return {k: v for k, v in asdict(self).items() if v is not None}

    def with_duration(self, duration_ms: float) -> LogContext:
        """Create a copy with duration set.

        Convenience method for timing operations.

        Args:
            duration_ms: Operation duration in milliseconds.

        Returns:
            New LogContext with duration set.

        Example:
            import time
            start = time.perf_counter()
            # ... do work ...
            duration_ms = (time.perf_counter() - start) * 1000
            ctx = base_ctx.with_duration(duration_ms)
        """
        return LogContext(
            correlation_id=self.correlation_id,
            operation=self.operation,
            entity_gid=self.entity_gid,
            entity_type=self.entity_type,
            duration_ms=duration_ms,
        )


__all__ = ["LogContext"]
