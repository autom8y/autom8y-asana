"""Cache metrics aggregation and event tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable


@dataclass
class CacheEvent:
    """Individual cache event for logging and callbacks.

    Represents a single cache operation with timing and context
    information for observability.

    Attributes:
        event_type: Type of event (hit, miss, write, evict, expire, error).
        key: Cache key involved in the operation.
        entry_type: Entry type if applicable, None otherwise.
        latency_ms: Operation latency in milliseconds.
        timestamp: When the event occurred.
        correlation_id: Optional correlation ID for request tracing.
        metadata: Additional event-specific context.
    """

    event_type: str
    key: str
    entry_type: str | None
    latency_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class CacheMetrics:
    """Thread-safe cache metrics aggregator.

    Tracks cache hit/miss rates, write counts, and other operational
    metrics. Supports callbacks for integration with external monitoring
    systems (CloudWatch, DataDog, etc.).

    Thread-safe: All operations use a lock to prevent race conditions
    in concurrent environments.

    Example:
        >>> metrics = CacheMetrics()
        >>> metrics.record_hit(latency_ms=2.5)
        >>> metrics.record_miss(latency_ms=1.0)
        >>> metrics.hit_rate
        0.5
        >>> metrics.api_calls_saved
        1
    """

    def __init__(self) -> None:
        """Initialize metrics with zeroed counters."""
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
        self._writes = 0
        self._evictions = 0
        self._errors = 0
        self._promotions = 0
        self._total_latency_ms = 0.0
        self._operation_count = 0
        self._overflow_skips: dict[str, int] = {}
        self._callbacks: list[Callable[[CacheEvent], None]] = []

    @property
    def hits(self) -> int:
        """Total cache hits."""
        with self._lock:
            return self._hits

    @property
    def misses(self) -> int:
        """Total cache misses."""
        with self._lock:
            return self._misses

    @property
    def writes(self) -> int:
        """Total cache writes."""
        with self._lock:
            return self._writes

    @property
    def evictions(self) -> int:
        """Total cache evictions (explicit invalidations)."""
        with self._lock:
            return self._evictions

    @property
    def errors(self) -> int:
        """Total cache operation errors."""
        with self._lock:
            return self._errors

    @property
    def promotions(self) -> int:
        """Total cache promotions (cold tier to hot tier)."""
        with self._lock:
            return self._promotions

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate as ratio (0.0 to 1.0).

        Returns:
            Hit rate as decimal, 0.0 if no operations recorded.
        """
        with self._lock:
            total = self._hits + self._misses
            return self._hits / total if total > 0 else 0.0

    @property
    def hit_rate_percent(self) -> float:
        """Calculate hit rate as percentage (0.0 to 100.0).

        Returns:
            Hit rate as percentage, 0.0 if no operations recorded.
        """
        return self.hit_rate * 100

    @property
    def api_calls_saved(self) -> int:
        """Estimate of API calls avoided by cache hits.

        Each cache hit represents one avoided API call.

        Returns:
            Number of API calls saved.
        """
        with self._lock:
            return self._hits

    @property
    def average_latency_ms(self) -> float:
        """Average operation latency in milliseconds.

        Returns:
            Average latency, 0.0 if no operations recorded.
        """
        with self._lock:
            if self._operation_count == 0:
                return 0.0
            return self._total_latency_ms / self._operation_count

    @property
    def overflow_skips(self) -> dict[str, int]:
        """Count of cache writes skipped due to overflow by entry type.

        Returns:
            Dict mapping entry type to skip count.
        """
        with self._lock:
            return self._overflow_skips.copy()

    def record_hit(
        self,
        latency_ms: float,
        key: str = "",
        entry_type: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Record a cache hit.

        Args:
            latency_ms: Operation latency in milliseconds.
            key: Cache key that was hit.
            entry_type: Entry type if applicable.
            correlation_id: Optional correlation ID for tracing.
        """
        with self._lock:
            self._hits += 1
            self._total_latency_ms += latency_ms
            self._operation_count += 1

        self._emit_event(
            CacheEvent(
                event_type="hit",
                key=key,
                entry_type=entry_type,
                latency_ms=latency_ms,
                correlation_id=correlation_id,
            )
        )

    def record_miss(
        self,
        latency_ms: float,
        key: str = "",
        entry_type: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Record a cache miss.

        Args:
            latency_ms: Operation latency in milliseconds.
            key: Cache key that missed.
            entry_type: Entry type if applicable.
            correlation_id: Optional correlation ID for tracing.
        """
        with self._lock:
            self._misses += 1
            self._total_latency_ms += latency_ms
            self._operation_count += 1

        self._emit_event(
            CacheEvent(
                event_type="miss",
                key=key,
                entry_type=entry_type,
                latency_ms=latency_ms,
                correlation_id=correlation_id,
            )
        )

    def record_write(
        self,
        latency_ms: float,
        key: str = "",
        entry_type: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Record a cache write.

        Args:
            latency_ms: Operation latency in milliseconds.
            key: Cache key that was written.
            entry_type: Entry type if applicable.
            correlation_id: Optional correlation ID for tracing.
        """
        with self._lock:
            self._writes += 1
            self._total_latency_ms += latency_ms
            self._operation_count += 1

        self._emit_event(
            CacheEvent(
                event_type="write",
                key=key,
                entry_type=entry_type,
                latency_ms=latency_ms,
                correlation_id=correlation_id,
            )
        )

    def record_eviction(
        self,
        key: str = "",
        entry_type: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Record a cache eviction (explicit invalidation).

        Args:
            key: Cache key that was evicted.
            entry_type: Entry type if applicable.
            correlation_id: Optional correlation ID for tracing.
        """
        with self._lock:
            self._evictions += 1

        self._emit_event(
            CacheEvent(
                event_type="evict",
                key=key,
                entry_type=entry_type,
                latency_ms=0.0,
                correlation_id=correlation_id,
            )
        )

    def record_error(
        self,
        key: str = "",
        entry_type: str | None = None,
        error_message: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Record a cache operation error.

        Args:
            key: Cache key involved in error.
            entry_type: Entry type if applicable.
            error_message: Error description.
            correlation_id: Optional correlation ID for tracing.
        """
        with self._lock:
            self._errors += 1

        metadata = {}
        if error_message:
            metadata["error"] = error_message

        self._emit_event(
            CacheEvent(
                event_type="error",
                key=key,
                entry_type=entry_type,
                latency_ms=0.0,
                correlation_id=correlation_id,
                metadata=metadata,
            )
        )

    def record_overflow_skip(
        self,
        entry_type: str,
        key: str = "",
        count: int | None = None,
        threshold: int | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Record a cache write skipped due to overflow.

        Args:
            entry_type: Entry type that exceeded threshold.
            key: Cache key that would have been written.
            count: Actual count that triggered overflow.
            threshold: Threshold that was exceeded.
            correlation_id: Optional correlation ID for tracing.
        """
        with self._lock:
            self._overflow_skips[entry_type] = self._overflow_skips.get(entry_type, 0) + 1

        metadata: dict[str, Any] = {}
        if count is not None:
            metadata["count"] = count
        if threshold is not None:
            metadata["threshold"] = threshold

        self._emit_event(
            CacheEvent(
                event_type="overflow_skip",
                key=key,
                entry_type=entry_type,
                latency_ms=0.0,
                correlation_id=correlation_id,
                metadata=metadata,
            )
        )

    def record_promotion(
        self,
        key: str = "",
        entry_type: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Record a cache promotion (cold tier to hot tier).

        Promotions occur when an entry is found in the cold tier (S3)
        and is copied to the hot tier (Redis) for faster subsequent access.

        Args:
            key: Cache key that was promoted.
            entry_type: Entry type if applicable.
            correlation_id: Optional correlation ID for tracing.
        """
        with self._lock:
            self._promotions += 1

        self._emit_event(
            CacheEvent(
                event_type="promotion",
                key=key,
                entry_type=entry_type,
                latency_ms=0.0,
                correlation_id=correlation_id,
            )
        )

    def on_event(self, callback: Callable[[CacheEvent], None]) -> None:
        """Register callback for cache events.

        Callbacks are invoked synchronously after each event is recorded.
        They should be fast to avoid blocking cache operations.

        Args:
            callback: Function to call with CacheEvent on each event.

        Example:
            >>> def log_event(event: CacheEvent) -> None:
            ...     print(f"{event.event_type}: {event.key}")
            >>> metrics.on_event(log_event)
        """
        with self._lock:
            self._callbacks.append(callback)

    def reset(self) -> None:
        """Reset all counters to zero.

        Useful for periodic metric collection or testing.
        """
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._writes = 0
            self._evictions = 0
            self._errors = 0
            self._promotions = 0
            self._total_latency_ms = 0.0
            self._operation_count = 0
            self._overflow_skips.clear()

    def snapshot(self) -> dict[str, Any]:
        """Get a snapshot of current metrics.

        Returns:
            Dict containing all current metric values.
        """
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "writes": self._writes,
                "evictions": self._evictions,
                "errors": self._errors,
                "promotions": self._promotions,
                "hit_rate": self._hits / (self._hits + self._misses)
                if (self._hits + self._misses) > 0
                else 0.0,
                "average_latency_ms": self._total_latency_ms / self._operation_count
                if self._operation_count > 0
                else 0.0,
                "overflow_skips": self._overflow_skips.copy(),
            }

    def _emit_event(self, event: CacheEvent) -> None:
        """Emit event to all registered callbacks.

        Args:
            event: CacheEvent to emit.
        """
        with self._lock:
            callbacks = self._callbacks.copy()

        for callback in callbacks:
            try:
                callback(event)
            except Exception:
                # Don't let callback errors break cache operations
                pass
