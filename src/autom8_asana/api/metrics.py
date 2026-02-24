"""Domain-specific Prometheus metrics for autom8_asana.

Metrics are registered on the default prometheus_client.REGISTRY and
served alongside autom8y_http_* platform metrics via the /metrics endpoint
provided by instrument_app().

All metric recording is in-memory (fire-and-forget) with no synchronous I/O.

Per TDD-SDK-ALIGNMENT Path 3: Domain-specific Prometheus metrics for ECS
FastAPI service observability.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# --- DataFrame Cache Metrics ---

DATAFRAME_BUILD_DURATION = Histogram(
    "asana_dataframe_build_duration_seconds",
    "Time to build a DataFrame from API data",
    labelnames=["entity_type"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

DATAFRAME_CACHE_OPS = Counter(
    "asana_dataframe_cache_operations_total",
    "DataFrame cache operations by tier and result",
    labelnames=["entity_type", "tier", "result"],
)

DATAFRAME_ROWS_CACHED = Gauge(
    "asana_dataframe_rows_cached",
    "Current row count in most recent cached DataFrame per entity type",
    labelnames=["entity_type"],
)

DATAFRAME_SWR_REFRESHES = Counter(
    "asana_dataframe_swr_refreshes_total",
    "Stale-while-revalidate background refresh attempts",
    labelnames=["entity_type", "result"],
)

DATAFRAME_CIRCUIT_BREAKER = Gauge(
    "asana_dataframe_circuit_breaker_state",
    "Circuit breaker state per project (0=closed, 1=open, 2=half_open)",
    labelnames=["project_gid"],
)

# --- Asana API Metrics ---
# These supplement the autom8y_http_* metrics from instrument_app() with
# domain-specific API call tracking at the Asana resource level.

ASANA_API_CALLS = Counter(
    "asana_api_calls_total",
    "Asana API calls by endpoint pattern and status",
    labelnames=["method", "path_pattern", "status_code"],
)

ASANA_API_DURATION = Histogram(
    "asana_api_call_duration_seconds",
    "Asana API call duration by endpoint pattern",
    labelnames=["method", "path_pattern"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


# --- Helper Recording Functions ---
# Fire-and-forget with no error propagation.


def record_build_duration(entity_type: str, duration_seconds: float) -> None:
    """Record DataFrame build duration."""
    DATAFRAME_BUILD_DURATION.labels(entity_type=entity_type).observe(duration_seconds)


def record_cache_op(
    entity_type: str,
    tier: str,
    result: str,
) -> None:
    """Record a cache operation (hit/miss/error).

    Args:
        entity_type: Entity type (e.g., "unit", "offer").
        tier: Cache tier ("memory" or "s3").
        result: Operation result ("hit", "miss", or "error").
    """
    DATAFRAME_CACHE_OPS.labels(
        entity_type=entity_type,
        tier=tier,
        result=result,
    ).inc()


def record_rows_cached(entity_type: str, row_count: int) -> None:
    """Update the rows-cached gauge for an entity type."""
    DATAFRAME_ROWS_CACHED.labels(entity_type=entity_type).set(row_count)


def record_swr_refresh(entity_type: str, result: str) -> None:
    """Record an SWR refresh attempt (success/failure)."""
    DATAFRAME_SWR_REFRESHES.labels(entity_type=entity_type, result=result).inc()


def record_circuit_breaker_state(project_gid: str, state: int) -> None:
    """Update circuit breaker state gauge.

    Args:
        project_gid: Project GID.
        state: 0=closed, 1=open, 2=half_open.
    """
    DATAFRAME_CIRCUIT_BREAKER.labels(project_gid=project_gid).set(state)


def record_api_call(
    method: str,
    path_pattern: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    """Record an Asana API call."""
    ASANA_API_CALLS.labels(
        method=method,
        path_pattern=path_pattern,
        status_code=str(status_code),
    ).inc()
    ASANA_API_DURATION.labels(
        method=method,
        path_pattern=path_pattern,
    ).observe(duration_seconds)


# --- Concrete MetricsEmitter Implementation ---
# Satisfies protocols.metrics.MetricsEmitter via structural typing.


class PrometheusMetricsEmitter:
    """Concrete MetricsEmitter backed by prometheus_client counters/gauges.

    Injected into DataFrameCache at startup to decouple cache layer from
    api layer (eliminates Cycle 5).
    """

    def record_cache_op(self, entity_type: str, tier: str, result: str) -> None:
        """Record a cache operation (hit/miss/error)."""
        DATAFRAME_CACHE_OPS.labels(
            entity_type=entity_type, tier=tier, result=result
        ).inc()

    def record_rows_cached(self, entity_type: str, row_count: int) -> None:
        """Update the rows-cached gauge for an entity type."""
        DATAFRAME_ROWS_CACHED.labels(entity_type=entity_type).set(row_count)

    def record_swr_refresh(self, entity_type: str, result: str) -> None:
        """Record an SWR refresh attempt (success/failure)."""
        DATAFRAME_SWR_REFRESHES.labels(entity_type=entity_type, result=result).inc()
