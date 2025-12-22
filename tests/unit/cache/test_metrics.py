"""Tests for CacheMetrics and CacheEvent."""

from datetime import datetime, timezone
from unittest.mock import MagicMock


from autom8_asana.cache.metrics import CacheEvent, CacheMetrics


class TestCacheEvent:
    """Tests for CacheEvent dataclass."""

    def test_create_event(self) -> None:
        """Test creating a cache event."""
        event = CacheEvent(
            event_type="hit",
            key="task:123",
            entry_type="task",
            latency_ms=2.5,
        )

        assert event.event_type == "hit"
        assert event.key == "task:123"
        assert event.entry_type == "task"
        assert event.latency_ms == 2.5

    def test_event_timestamp_default(self) -> None:
        """Test event timestamp defaults to now."""
        before = datetime.now(timezone.utc)
        event = CacheEvent(
            event_type="hit",
            key="key",
            entry_type=None,
            latency_ms=1.0,
        )
        after = datetime.now(timezone.utc)

        assert before <= event.timestamp <= after

    def test_event_with_correlation_id(self) -> None:
        """Test event with correlation ID."""
        event = CacheEvent(
            event_type="miss",
            key="key",
            entry_type=None,
            latency_ms=1.0,
            correlation_id="abc-123",
        )

        assert event.correlation_id == "abc-123"

    def test_event_with_metadata(self) -> None:
        """Test event with metadata."""
        event = CacheEvent(
            event_type="error",
            key="key",
            entry_type=None,
            latency_ms=0.0,
            metadata={"error": "Connection refused"},
        )

        assert event.metadata["error"] == "Connection refused"

    def test_event_metadata_default_empty(self) -> None:
        """Test event metadata defaults to empty dict."""
        event = CacheEvent(
            event_type="hit",
            key="key",
            entry_type=None,
            latency_ms=1.0,
        )

        assert event.metadata == {}


class TestCacheMetrics:
    """Tests for CacheMetrics class."""

    def test_initial_state(self) -> None:
        """Test initial metrics are zero."""
        metrics = CacheMetrics()

        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.writes == 0
        assert metrics.evictions == 0
        assert metrics.errors == 0
        assert metrics.hit_rate == 0.0
        assert metrics.api_calls_saved == 0
        assert metrics.average_latency_ms == 0.0
        assert metrics.overflow_skips == {}

    def test_record_hit(self) -> None:
        """Test recording a cache hit."""
        metrics = CacheMetrics()
        metrics.record_hit(latency_ms=2.5)

        assert metrics.hits == 1
        assert metrics.api_calls_saved == 1

    def test_record_hit_with_details(self) -> None:
        """Test recording a hit with full details."""
        metrics = CacheMetrics()
        metrics.record_hit(
            latency_ms=2.5,
            key="task:123",
            entry_type="task",
            correlation_id="abc-123",
        )

        assert metrics.hits == 1

    def test_record_miss(self) -> None:
        """Test recording a cache miss."""
        metrics = CacheMetrics()
        metrics.record_miss(latency_ms=1.0)

        assert metrics.misses == 1

    def test_record_write(self) -> None:
        """Test recording a cache write."""
        metrics = CacheMetrics()
        metrics.record_write(latency_ms=5.0)

        assert metrics.writes == 1

    def test_record_eviction(self) -> None:
        """Test recording a cache eviction."""
        metrics = CacheMetrics()
        metrics.record_eviction()

        assert metrics.evictions == 1

    def test_record_error(self) -> None:
        """Test recording a cache error."""
        metrics = CacheMetrics()
        metrics.record_error(error_message="Connection refused")

        assert metrics.errors == 1

    def test_record_overflow_skip(self) -> None:
        """Test recording an overflow skip."""
        metrics = CacheMetrics()
        metrics.record_overflow_skip(
            entry_type="subtasks",
            count=100,
            threshold=40,
        )

        assert metrics.overflow_skips == {"subtasks": 1}

    def test_overflow_skip_accumulates(self) -> None:
        """Test overflow skips accumulate by type."""
        metrics = CacheMetrics()
        metrics.record_overflow_skip(entry_type="subtasks")
        metrics.record_overflow_skip(entry_type="subtasks")
        metrics.record_overflow_skip(entry_type="stories")

        assert metrics.overflow_skips["subtasks"] == 2
        assert metrics.overflow_skips["stories"] == 1

    def test_hit_rate_calculation(self) -> None:
        """Test hit rate calculation."""
        metrics = CacheMetrics()
        metrics.record_hit(latency_ms=1.0)
        metrics.record_hit(latency_ms=1.0)
        metrics.record_miss(latency_ms=1.0)
        metrics.record_miss(latency_ms=1.0)

        assert metrics.hit_rate == 0.5  # 2 hits / 4 total

    def test_hit_rate_percent(self) -> None:
        """Test hit rate as percentage."""
        metrics = CacheMetrics()
        metrics.record_hit(latency_ms=1.0)
        metrics.record_miss(latency_ms=1.0)

        assert metrics.hit_rate_percent == 50.0

    def test_hit_rate_zero_when_no_operations(self) -> None:
        """Test hit rate is 0 when no operations."""
        metrics = CacheMetrics()

        assert metrics.hit_rate == 0.0

    def test_average_latency(self) -> None:
        """Test average latency calculation."""
        metrics = CacheMetrics()
        metrics.record_hit(latency_ms=2.0)
        metrics.record_hit(latency_ms=4.0)
        metrics.record_miss(latency_ms=6.0)

        assert metrics.average_latency_ms == 4.0  # (2 + 4 + 6) / 3

    def test_average_latency_zero_when_no_operations(self) -> None:
        """Test average latency is 0 when no operations."""
        metrics = CacheMetrics()

        assert metrics.average_latency_ms == 0.0

    def test_reset(self) -> None:
        """Test reset clears all counters."""
        metrics = CacheMetrics()
        metrics.record_hit(latency_ms=1.0)
        metrics.record_miss(latency_ms=1.0)
        metrics.record_write(latency_ms=1.0)
        metrics.record_eviction()
        metrics.record_error()
        metrics.record_overflow_skip(entry_type="subtasks")

        metrics.reset()

        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.writes == 0
        assert metrics.evictions == 0
        assert metrics.errors == 0
        assert metrics.overflow_skips == {}
        assert metrics.average_latency_ms == 0.0

    def test_snapshot(self) -> None:
        """Test snapshot returns current metrics."""
        metrics = CacheMetrics()
        metrics.record_hit(latency_ms=2.0)
        metrics.record_miss(latency_ms=2.0)
        metrics.record_write(latency_ms=2.0)

        snapshot = metrics.snapshot()

        assert snapshot["hits"] == 1
        assert snapshot["misses"] == 1
        assert snapshot["writes"] == 1
        assert snapshot["hit_rate"] == 0.5
        assert snapshot["average_latency_ms"] == 2.0

    def test_on_event_callback(self) -> None:
        """Test event callbacks are called."""
        metrics = CacheMetrics()
        callback = MagicMock()
        metrics.on_event(callback)

        metrics.record_hit(latency_ms=1.0, key="test")

        callback.assert_called_once()
        event = callback.call_args[0][0]
        assert isinstance(event, CacheEvent)
        assert event.event_type == "hit"

    def test_multiple_callbacks(self) -> None:
        """Test multiple callbacks are all called."""
        metrics = CacheMetrics()
        callback1 = MagicMock()
        callback2 = MagicMock()
        metrics.on_event(callback1)
        metrics.on_event(callback2)

        metrics.record_hit(latency_ms=1.0)

        callback1.assert_called_once()
        callback2.assert_called_once()

    def test_callback_error_does_not_break_metrics(self) -> None:
        """Test callback errors don't break metric recording."""
        metrics = CacheMetrics()

        def bad_callback(event: CacheEvent) -> None:
            raise RuntimeError("Callback error")

        metrics.on_event(bad_callback)

        # Should not raise
        metrics.record_hit(latency_ms=1.0)
        assert metrics.hits == 1

    def test_thread_safety(self) -> None:
        """Test metrics are thread-safe."""
        import threading

        metrics = CacheMetrics()
        num_threads = 10
        ops_per_thread = 100

        def record_ops():
            for _ in range(ops_per_thread):
                metrics.record_hit(latency_ms=1.0)
                metrics.record_miss(latency_ms=1.0)

        threads = [threading.Thread(target=record_ops) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        expected_hits = num_threads * ops_per_thread
        expected_misses = num_threads * ops_per_thread

        assert metrics.hits == expected_hits
        assert metrics.misses == expected_misses

    def test_callback_receives_correct_event_types(self) -> None:
        """Test callbacks receive correct event types for each operation."""
        metrics = CacheMetrics()
        events: list[CacheEvent] = []

        def collect_events(event: CacheEvent) -> None:
            events.append(event)

        metrics.on_event(collect_events)

        metrics.record_hit(latency_ms=1.0)
        metrics.record_miss(latency_ms=1.0)
        metrics.record_write(latency_ms=1.0)
        metrics.record_eviction()
        metrics.record_error()
        metrics.record_overflow_skip(entry_type="test")

        event_types = [e.event_type for e in events]
        assert "hit" in event_types
        assert "miss" in event_types
        assert "write" in event_types
        assert "evict" in event_types
        assert "error" in event_types
        assert "overflow_skip" in event_types
