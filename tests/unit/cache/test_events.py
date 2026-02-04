"""Tests for cache event integration with LogProvider."""

import logging
from typing import Any

from autom8_asana.cache.models.events import (
    _normalize_event_type,
    create_metrics_callback,
    has_cache_logging,
    setup_cache_logging,
)
from autom8_asana.cache.models.metrics import CacheEvent, CacheMetrics


class MockCacheLoggingProvider:
    """Mock LogProvider that supports cache logging."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def log_cache_event(
        self,
        event_type: str,
        key: str,
        entry_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.events.append(
            {
                "event_type": event_type,
                "key": key,
                "entry_type": entry_type,
                "metadata": metadata,
            }
        )


class MockCacheProvider:
    """Mock cache provider with metrics."""

    def __init__(self) -> None:
        self._metrics = CacheMetrics()

    def get_metrics(self) -> CacheMetrics:
        return self._metrics


class TestCreateMetricsCallback:
    """Tests for create_metrics_callback function."""

    def test_callback_routes_to_log_provider(self) -> None:
        """Test that callback routes events to log provider."""
        log_provider = MockCacheLoggingProvider()
        callback = create_metrics_callback(log_provider)

        event = CacheEvent(
            event_type="hit",
            key="task:123",
            entry_type="task",
            latency_ms=2.5,
        )

        callback(event)

        assert len(log_provider.events) == 1
        logged = log_provider.events[0]
        assert logged["event_type"] == "hit"
        assert logged["key"] == "task:123"
        assert logged["entry_type"] == "task"
        assert logged["metadata"]["latency_ms"] == 2.5

    def test_callback_includes_correlation_id(self) -> None:
        """Test that callback includes correlation ID in metadata."""
        log_provider = MockCacheLoggingProvider()
        callback = create_metrics_callback(log_provider)

        event = CacheEvent(
            event_type="miss",
            key="task:456",
            entry_type="task",
            latency_ms=1.0,
            correlation_id="corr-123",
        )

        callback(event)

        logged = log_provider.events[0]
        assert logged["metadata"]["correlation_id"] == "corr-123"

    def test_callback_merges_event_metadata(self) -> None:
        """Test that callback merges event metadata."""
        log_provider = MockCacheLoggingProvider()
        callback = create_metrics_callback(log_provider)

        event = CacheEvent(
            event_type="overflow_skip",
            key="task:789",
            entry_type="subtasks",
            latency_ms=0.0,
            metadata={"count": 100, "threshold": 40},
        )

        callback(event)

        logged = log_provider.events[0]
        assert logged["metadata"]["count"] == 100
        assert logged["metadata"]["threshold"] == 40

    def test_callback_handles_empty_key(self) -> None:
        """Test that callback handles empty key."""
        log_provider = MockCacheLoggingProvider()
        callback = create_metrics_callback(log_provider)

        event = CacheEvent(
            event_type="error",
            key="",
            entry_type=None,
            latency_ms=0.0,
        )

        callback(event)

        logged = log_provider.events[0]
        assert logged["key"] == ""

    def test_callback_handles_no_metadata(self) -> None:
        """Test that callback handles events with no metadata."""
        log_provider = MockCacheLoggingProvider()
        callback = create_metrics_callback(log_provider)

        event = CacheEvent(
            event_type="hit",
            key="task:123",
            entry_type="task",
            latency_ms=0.0,  # Zero latency
        )

        callback(event)

        # Should still have metadata (empty dict for latency_ms=0)
        assert len(log_provider.events) == 1


class TestNormalizeEventType:
    """Tests for _normalize_event_type function."""

    def test_normalizes_valid_types(self) -> None:
        """Test normalization of valid event types."""
        assert _normalize_event_type("hit") == "hit"
        assert _normalize_event_type("miss") == "miss"
        assert _normalize_event_type("write") == "write"
        assert _normalize_event_type("evict") == "evict"
        assert _normalize_event_type("expire") == "expire"
        assert _normalize_event_type("error") == "error"
        assert _normalize_event_type("overflow_skip") == "overflow_skip"

    def test_normalizes_unknown_to_error(self) -> None:
        """Test that unknown types default to error."""
        assert _normalize_event_type("unknown") == "error"
        assert _normalize_event_type("") == "error"
        assert _normalize_event_type("custom_event") == "error"


class TestSetupCacheLogging:
    """Tests for setup_cache_logging function."""

    def test_wires_metrics_to_log_provider(self) -> None:
        """Test that setup wires metrics to log provider."""
        cache_provider = MockCacheProvider()
        log_provider = MockCacheLoggingProvider()

        setup_cache_logging(cache_provider, log_provider)

        # Now record an event through metrics
        cache_provider.get_metrics().record_hit(
            latency_ms=2.5,
            key="task:123",
            entry_type="task",
        )

        # Event should appear in log provider
        assert len(log_provider.events) == 1
        assert log_provider.events[0]["event_type"] == "hit"

    def test_multiple_events_routed(self) -> None:
        """Test that multiple events are all routed."""
        cache_provider = MockCacheProvider()
        log_provider = MockCacheLoggingProvider()

        setup_cache_logging(cache_provider, log_provider)

        metrics = cache_provider.get_metrics()
        metrics.record_hit(latency_ms=1.0, key="k1")
        metrics.record_miss(latency_ms=1.0, key="k2")
        metrics.record_write(latency_ms=1.0, key="k3")

        assert len(log_provider.events) == 3


class TestHasCacheLogging:
    """Tests for has_cache_logging function."""

    def test_returns_true_for_provider_with_method(self) -> None:
        """Test returns True for provider with log_cache_event."""
        log_provider = MockCacheLoggingProvider()
        assert has_cache_logging(log_provider) is True

    def test_returns_false_for_standard_logger(self) -> None:
        """Test returns False for standard logging.Logger."""
        logger = logging.getLogger("test")
        assert has_cache_logging(logger) is False

    def test_returns_false_for_object_without_method(self) -> None:
        """Test returns False for object without log_cache_event."""

        class SimpleLogger:
            def debug(self, msg: str) -> None:
                pass

        assert has_cache_logging(SimpleLogger()) is False

    def test_returns_false_for_non_callable_attribute(self) -> None:
        """Test returns False when log_cache_event is not callable."""

        class FakeProvider:
            log_cache_event = "not a method"

        assert has_cache_logging(FakeProvider()) is False


class TestDefaultLogProviderIntegration:
    """Integration tests with DefaultLogProvider."""

    def test_default_log_provider_has_method(self) -> None:
        """Test DefaultLogProvider implements log_cache_event."""
        from autom8_asana._defaults.log import DefaultLogProvider

        log_provider = DefaultLogProvider()
        assert has_cache_logging(log_provider) is True

    def test_default_log_provider_logs_event(self) -> None:
        """Test DefaultLogProvider logs cache events."""
        from autom8_asana._defaults.log import DefaultLogProvider

        log_provider = DefaultLogProvider(level=logging.DEBUG)

        # Should not raise
        log_provider.log_cache_event(
            event_type="hit",
            key="task:123",
            entry_type="task",
            metadata={"latency_ms": 2.5},
        )

    def test_cache_logging_can_be_disabled(self) -> None:
        """Test that cache logging can be disabled."""
        from autom8_asana._defaults.log import DefaultLogProvider

        log_provider = DefaultLogProvider(
            level=logging.DEBUG,
            enable_cache_logging=False,
        )

        # Should not raise, but also should not log
        log_provider.log_cache_event(
            event_type="hit",
            key="task:123",
        )


class TestEndToEndCacheLogging:
    """End-to-end tests for cache logging."""

    def test_full_pipeline(self) -> None:
        """Test full pipeline from cache operation to log."""
        from autom8_asana._defaults.log import DefaultLogProvider

        # Create components
        cache_provider = MockCacheProvider()
        log_provider = DefaultLogProvider(level=logging.DEBUG)

        # Wire them up
        setup_cache_logging(cache_provider, log_provider)

        # Trigger cache events
        metrics = cache_provider.get_metrics()
        metrics.record_hit(latency_ms=2.5, key="task:123", entry_type="task")
        metrics.record_miss(latency_ms=1.0, key="task:456", entry_type="task")
        metrics.record_eviction(key="task:789")

        # Verify metrics were recorded
        assert metrics.hits == 1
        assert metrics.misses == 1
        assert metrics.evictions == 1
