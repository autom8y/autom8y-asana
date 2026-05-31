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
    "autom8y_asana_dataframe_build_duration_seconds",
    "Time to build a DataFrame from API data",
    labelnames=["entity_type"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

DATAFRAME_CACHE_OPS = Counter(
    "autom8y_asana_dataframe_cache_operations_total",
    "DataFrame cache operations by tier and result",
    labelnames=["entity_type", "tier", "result"],
)

DATAFRAME_ROWS_CACHED = Gauge(
    "autom8y_asana_dataframe_rows_cached",
    "Current row count in most recent cached DataFrame per entity type",
    labelnames=["entity_type"],
)

DATAFRAME_SWR_REFRESHES = Counter(
    "autom8y_asana_dataframe_swr_refreshes_total",
    "Stale-while-revalidate background refresh attempts",
    labelnames=["entity_type", "result"],
)

DATAFRAME_CIRCUIT_BREAKER = Gauge(
    "autom8y_asana_dataframe_circuit_breaker_state",
    "Circuit breaker state per project (0=closed, 1=open, 2=half_open)",
    labelnames=["project_gid"],
)

# --- Asana API Metrics ---
# These supplement the autom8y_http_* metrics from instrument_app() with
# domain-specific API call tracking at the Asana resource level.

ASANA_API_CALLS = Counter(
    "autom8y_asana_api_calls_total",
    "Asana API calls by endpoint pattern and status",
    labelnames=["method", "path_pattern", "status_code"],
)

ASANA_API_DURATION = Histogram(
    "autom8y_asana_api_call_duration_seconds",
    "Asana API call duration by endpoint pattern",
    labelnames=["method", "path_pattern"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


# --- receiver-bulk-fanout-reliability Stage-1 metrics ---
# Per .sos/wip/thermia/observability-plan.md §Stage-1 metrics.
# All emit on the request hot path; keep recording functions fast (no I/O).

# §1.1 — Cache lookup outcomes. ``cache_miss_rate`` (the alert target) is a
# derived gauge computed at query-time as miss / (miss + hit). The receiver
# emits only the underlying counters; rate-of-change alerting runs in the
# CloudWatch/metrics pipeline (Alert A1 — MISS-RATE-SPIKE).
CACHE_LOOKUP_OUTCOME = Counter(
    "autom8y_asana_cache_lookup_outcome_total",
    "DataFrame cache lookup outcomes for the body-parameterized path",
    labelnames=["entity_type", "outcome"],  # outcome: hit | miss
)

# §1.2 — BuildCoordinator semaphore utilization. Gauge in [0, 1] = in-flight /
# max_concurrent_builds. Alert A5 (SEMAPHORE-SATURATION) fires at >0.80 for
# 5min — derived from Phase-3 Knob 1 (80% of 4 slots = 3.2 concurrent).
BUILD_COORDINATOR_SEMAPHORE_UTILIZATION = Gauge(
    "autom8y_asana_build_coordinator_semaphore_utilization",
    "Fraction of BuildCoordinator semaphore slots in use (in-flight / max)",
)

# §1.3 — Per-namespace 429 split. Existing ``http_429_count`` is undifferentiated;
# this counter splits by rate-limit key namespace (sa: / pat: / ip:) so the
# Stage-1 alert A3 (SA-BUCKET-429) can target the SA bucket specifically.
RATE_LIMIT_429_BY_NAMESPACE = Counter(
    "autom8y_asana_rate_limit_429_total",
    "HTTP 429 responses split by rate-limit key namespace",
    labelnames=["namespace"],  # sa | pat | ip | other
)

# §1.6 — Receiver-side mirror SLI. Per-entity-arm success rate is the deploy
# gate's primary metric (§3 deploy-gate criterion). Counters split by arm so
# the consumer's Autom8y/AsanaDataframeSource satellite% can be tracked here
# within +/-1% without requiring the consumer's CloudWatch to populate first.
RECEIVER_QUERY_OUTCOME = Counter(
    "autom8y_asana_receiver_query_outcome_total",
    "Receiver-side query outcomes for body-parameterized arms (project, section)",
    labelnames=["entity_type", "outcome"],  # outcome: success | server_error
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


# --- Stage-1 helpers (receiver-bulk-fanout-reliability) ---


def record_cache_lookup(entity_type: str, hit: bool) -> None:
    """Record a DataFrame cache lookup outcome.

    Drives the ``cache_miss_rate`` derived gauge (Alert A1 — MISS-RATE-SPIKE).
    Per observability-plan.md §1.1: incremented at the universal_strategy
    cache-get branch (hit vs absolute miss).

    Args:
        entity_type: Body-parameterized entity (e.g., "project", "section").
        hit: True when ``cache.get_async`` returned non-None; False on
            absolute miss (None return — the path that triggers
            ``_build_on_miss`` and emits a 503).
    """
    outcome = "hit" if hit else "miss"
    CACHE_LOOKUP_OUTCOME.labels(entity_type=entity_type, outcome=outcome).inc()


def record_build_coordinator_utilization(
    in_flight: int,
    max_concurrent: int,
) -> None:
    """Update the BuildCoordinator semaphore utilization gauge.

    Per observability-plan.md §1.2 (Alert A5 — SEMAPHORE-SATURATION at >0.80
    for 5min). Updated on each acquire/release in the coordinator hot path.

    Args:
        in_flight: Current count of in-flight builds (semaphore slots held).
        max_concurrent: Configured ``max_concurrent_builds``.
    """
    if max_concurrent <= 0:
        return  # defensive: avoid div-by-zero
    BUILD_COORDINATOR_SEMAPHORE_UTILIZATION.set(in_flight / max_concurrent)


def record_rate_limit_429(namespace: str) -> None:
    """Record a 429 response by rate-limit key namespace.

    Per observability-plan.md §1.3 (Alert A3 — SA-BUCKET-429 fires when
    namespace=='sa' rate exceeds 1/min sustained for 2min). Namespace is
    the prefix of the rate-limit key returned by
    ``_get_rate_limit_key`` (sa / pat / ip).

    Args:
        namespace: Key namespace prefix ("sa" | "pat" | "ip" | "other").
            Unknown values are accepted; the dashboard surfaces them under
            the "other" tile so the operator catches unexpected key shapes.
    """
    safe_ns = namespace if namespace in {"sa", "pat", "ip"} else "other"
    RATE_LIMIT_429_BY_NAMESPACE.labels(namespace=safe_ns).inc()


def record_receiver_query_outcome(entity_type: str, success: bool) -> None:
    """Record a receiver query outcome (the mirror SLI primary metric).

    Per observability-plan.md §1.6: ``receiver_query_success_rate_{arm}`` is
    the deploy gate's primary signal (§3 deploy-gate criterion >=99% on both
    arms for 10min). Should track within +/-1% of the consumer's
    Autom8y/AsanaDataframeSource satellite% per arm.

    Args:
        entity_type: Body-parameterized arm ("project" | "section").
        success: True on 2xx; False on 5xx. 4xx is NOT counted (client error).
    """
    outcome = "success" if success else "server_error"
    RECEIVER_QUERY_OUTCOME.labels(entity_type=entity_type, outcome=outcome).inc()


# --- Concrete MetricsEmitter Implementation ---
# Satisfies protocols.metrics.MetricsEmitter via structural typing.


class PrometheusMetricsEmitter:
    """Concrete MetricsEmitter backed by prometheus_client counters/gauges.

    Injected into DataFrameCache at startup to decouple cache layer from
    api layer (eliminates Cycle 5).
    """

    def record_cache_op(self, entity_type: str, tier: str, result: str) -> None:
        """Record a cache operation (hit/miss/error)."""
        DATAFRAME_CACHE_OPS.labels(entity_type=entity_type, tier=tier, result=result).inc()

    def record_rows_cached(self, entity_type: str, row_count: int) -> None:
        """Update the rows-cached gauge for an entity type."""
        DATAFRAME_ROWS_CACHED.labels(entity_type=entity_type).set(row_count)

    def record_swr_refresh(self, entity_type: str, result: str) -> None:
        """Record an SWR refresh attempt (success/failure)."""
        DATAFRAME_SWR_REFRESHES.labels(entity_type=entity_type, result=result).inc()
