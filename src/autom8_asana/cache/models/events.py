"""Cache event integration with LogProvider.

Per ADR-0023, this module provides callbacks to route cache metrics
from CacheMetrics to LogProvider for observability.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from autom8_asana.cache.models.metrics import CacheEvent

if TYPE_CHECKING:
    from autom8_asana.protocols.cache import CacheProvider
    from autom8_asana.protocols.log import CacheEventType, CacheLoggingProvider


def create_metrics_callback(
    log_provider: CacheLoggingProvider,
) -> Callable[[CacheEvent], None]:
    """Create a CacheMetrics callback that routes events to LogProvider.

    Per ADR-0023, this bridges the gap between CacheMetrics (internal)
    and LogProvider (external observability).

    Args:
        log_provider: A LogProvider that implements log_cache_event.

    Returns:
        Callback function for CacheMetrics.on_event().

    Example:
        >>> from autom8_asana.cache import CacheMetrics
        >>> from autom8_asana._defaults.log import DefaultLogProvider
        >>>
        >>> metrics = CacheMetrics()
        >>> log_provider = DefaultLogProvider()
        >>> callback = create_metrics_callback(log_provider)
        >>> metrics.on_event(callback)
        >>>
        >>> # Now cache events will be logged
        >>> metrics.record_hit(latency_ms=2.5, key="task:123")
    """

    def callback(event: CacheEvent) -> None:
        # Map event_type to CacheEventType
        event_type: CacheEventType = _normalize_event_type(event.event_type)

        # Build metadata dict
        metadata: dict[str, Any] = {}
        if event.latency_ms:
            metadata["latency_ms"] = event.latency_ms
        if event.correlation_id:
            metadata["correlation_id"] = event.correlation_id
        if event.metadata:
            metadata.update(event.metadata)

        log_provider.log_cache_event(
            event_type=event_type,
            key=event.key or "",
            entry_type=event.entry_type,
            metadata=metadata if metadata else None,
        )

    return callback


def _normalize_event_type(event_type: str) -> CacheEventType:
    """Normalize event type string to valid CacheEventType.

    Args:
        event_type: Raw event type from CacheEvent.

    Returns:
        Valid CacheEventType literal.
    """
    # Map known event types
    valid_types = {"hit", "miss", "write", "evict", "expire", "error", "overflow_skip"}
    if event_type in valid_types:
        return event_type  # type: ignore[return-value]
    # Default unknown types to error
    return "error"


def setup_cache_logging(
    cache_provider: CacheProvider,
    log_provider: CacheLoggingProvider,
) -> None:
    """Wire up cache provider metrics to log provider.

    Call this during SDK initialization to enable cache observability.
    After setup, all cache operations will emit events to the log provider.

    Args:
        cache_provider: Cache provider with metrics support.
        log_provider: Log provider implementing log_cache_event.

    Example:
        >>> from autom8_asana.cache.backends.memory import InMemoryCacheProvider
        >>> from autom8_asana._defaults.log import DefaultLogProvider
        >>>
        >>> cache = InMemoryCacheProvider()
        >>> log = DefaultLogProvider()
        >>> setup_cache_logging(cache, log)
    """
    metrics = cache_provider.get_metrics()
    callback = create_metrics_callback(log_provider)
    metrics.on_event(callback)


def has_cache_logging(log_provider: Any) -> bool:
    """Check if a log provider supports cache logging.

    Use this to safely check before calling log_cache_event,
    especially when working with standard logging.Logger instances.

    Args:
        log_provider: Any log provider instance.

    Returns:
        True if the provider has a log_cache_event method.

    Example:
        >>> import logging
        >>> logger = logging.getLogger("test")
        >>> has_cache_logging(logger)
        False
        >>> from autom8_asana._defaults.log import DefaultLogProvider
        >>> has_cache_logging(DefaultLogProvider())
        True
    """
    return callable(getattr(log_provider, "log_cache_event", None))
