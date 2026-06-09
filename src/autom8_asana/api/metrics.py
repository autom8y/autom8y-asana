"""Domain-specific Prometheus metrics for autom8_asana.

Metrics are registered on the default prometheus_client.REGISTRY and
served alongside autom8y_http_* platform metrics via the /metrics endpoint
provided by instrument_app().

All metric recording is in-memory (fire-and-forget) with no synchronous I/O.

Per TDD-SDK-ALIGNMENT Path 3: Domain-specific Prometheus metrics for ECS
FastAPI service observability.
"""

from __future__ import annotations

import json
import os
import sys
import time

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

# --- S7-GATE-FIDELITY: 3-cause fallback disaggregation ---
# Per HANDOFF-autom8-to-asana-sre-cr3-producer-work-queue-ingest §4.1 and
# cr3-verified-findings §SYNTHESIS item 4 (the "S7 false-green guard").
#
# The consumer's single ``GetDfFallback`` EMF signal collapses THREE distinct
# causes into one counter; a Stage-B (fallback-deletion) decision read off a
# collapsed total is dangerous because the three causes have different
# remediations and different consequences:
#
#   * cadence_503   — CACHE_BUILD_IN_PROGRESS: a coalesced request waited for an
#                     in-flight build past ``CACHE_BUILD_WAIT_TIMEOUT`` (a warmth /
#                     cadence gap — the frame is being built; fixed by warming).
#   * capacity_502  — DATAFRAME_BUILD_{FAILED,ERROR,TIMEOUT,UNAVAILABLE}: the
#                     request-time build itself failed/timed-out — the
#                     build-semaphore-starvation path that escalates to an ALB 502
#                     (fixed by build headroom + CPU/mem, NOT warming).
#   * honest_refusal — an attested honest-empty 200 (``meta.honest_empty``): a
#                     genuinely-empty honest-complete project served as an empty
#                     2xx by contract — NOT a failure, but it MUST be distinguished
#                     from a real-data 2xx so a liveness-masquerade (empty 2xx
#                     counted as a healthy serve) cannot read green at the gate.
#
# This is the receiver-side disaggregation. It is ADDITIVE to (does not replace)
# RECEIVER_QUERY_OUTCOME, which remains the deploy-gate SLI denominator. The S7
# verdict reads CAUSE from this counter instead of inferring it from a collapsed
# success/server_error split.
RECEIVER_QUERY_FALLBACK_CAUSE = Counter(
    "autom8y_asana_receiver_query_fallback_cause_total",
    "Receiver-side query outcomes disaggregated by S7 cause: the three causes "
    "the consumer GetDfFallback collapses into one signal (cadence_503 / "
    "capacity_502 / honest_refusal). Lets the S7 fallback-retirement verdict "
    "read CAUSE, not a collapsed total.",
    labelnames=["entity_type", "cause"],  # cause: cadence_503 | capacity_502 | honest_refusal
)

# The three named S7 causes. Authoritative source for callers/dashboards/gate so
# the label vocabulary cannot drift. ``data_2xx`` is the fourth, non-fallback
# outcome (a real-data success) — tracked so honest_refusal can be read AGAINST
# the real-data serve count (the liveness-masquerade defeat: empty 2xx must be
# separable from real-data 2xx).
S7_CAUSE_CADENCE_503 = "cadence_503"
S7_CAUSE_CAPACITY_502 = "capacity_502"
S7_CAUSE_HONEST_REFUSAL = "honest_refusal"
S7_OUTCOME_DATA_2XX = "data_2xx"
S7_FALLBACK_CAUSES = (
    S7_CAUSE_CADENCE_503,
    S7_CAUSE_CAPACITY_502,
    S7_CAUSE_HONEST_REFUSAL,
)

# Map a 503 ``ApiDataFrameBuildError.code`` to its S7 cause. CACHE_BUILD_IN_PROGRESS
# is the cadence/warmth gap; every other build-error code is the capacity path that
# escalates to an ALB 502. Centralized here so the query route does not hardcode the
# string set and the two cannot drift apart.
_BUILD_CODE_TO_S7_CAUSE = {
    "CACHE_BUILD_IN_PROGRESS": S7_CAUSE_CADENCE_503,
    "DATAFRAME_BUILD_FAILED": S7_CAUSE_CAPACITY_502,
    "DATAFRAME_BUILD_ERROR": S7_CAUSE_CAPACITY_502,
    "DATAFRAME_BUILD_TIMEOUT": S7_CAUSE_CAPACITY_502,
    "DATAFRAME_BUILD_UNAVAILABLE": S7_CAUSE_CAPACITY_502,
}


def s7_cause_for_build_code(code: str) -> str:
    """Resolve the S7 cause for an ``ApiDataFrameBuildError`` code.

    ``CACHE_BUILD_IN_PROGRESS`` is the cadence/warmth gap (cadence_503); every
    other build-error code (FAILED / ERROR / TIMEOUT / UNAVAILABLE) is the
    capacity-starvation path (capacity_502). An unknown code defaults to
    capacity_502 — a build error we cannot classify is treated as the more
    consequential (Stage-B-blocking) capacity cause, never silently as cadence.
    """
    return _BUILD_CODE_TO_S7_CAUSE.get(code, S7_CAUSE_CAPACITY_502)


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


# --- CR-3 GATE-2 P2-a: receiver self-measurement EMF export (additive) ---
# Per TDD-cr3-gate2-receiver-self-measurement-export-2026-06-08.md (Option A).
#
# The process-local RECEIVER_QUERY_OUTCOME counter cannot self-prove the deploy
# gate's 10-min >=99% claim: it resets on every ECS task replacement, is not
# fleet-aggregated, and has no durable sink (TDD §"Why the process-local counter
# cannot self-prove"). This emitter writes one Embedded Metric Format (EMF) JSON
# line to stdout per request so a (cross-repo-configured) CloudWatch Logs + EMF
# extraction pipeline produces a durable, deploy-surviving, fleet-aggregated time
# series the gate can query AFTER the soak window.
#
# Emission is ADDITIVE — it mirrors the OBS-EXPORTS-001 precedent verbatim
# (this module, "Emission is ADDITIVE — no pipeline step, helper, or engine
# surface is altered"): record_receiver_query_outcome and the counter
# definitions are untouched; this is a new emitter at the existing seam.
#
# Hot-path safety (the decisive constraint, this module's line-7 invariant):
# the body is a single json.dumps + sys.stdout.write to stdout — no synchronous
# network I/O — and is wrapped in a broad try/except so a serialization error can never
# block or raise on the request path (fire-and-forget, "never raises on the
# fire-and-forget path").
#
# Ship-dark: gated behind RECEIVER_SLI_EMF_ENABLED (default off) so it can land
# before cross-repo handoff #1 (log driver = awslogs + EMF extraction) is
# confirmed, preventing stdout-volume surprise before the sink exists.

# Published cross-repo metric contract (TDD §"Data Model"; renaming is a
# breaking change to the monorepo alarm/gate consumer — ADR-RECEIVER-SLI-METRIC-CONTRACT).
RECEIVER_SLI_EMF_NAMESPACE = "Autom8y/AsanaReceiverSLI"
RECEIVER_SLI_EMF_FLAG_ENV = "RECEIVER_SLI_EMF_ENABLED"


def _receiver_sli_emf_enabled() -> bool:
    """Return True when the EMF emitter is flag-enabled (ship-dark default off).

    Read at call time (not import time) so the flag can be flipped per-task
    without a code change once cross-repo handoff #1 is confirmed. Accepts the
    usual truthy spellings; anything else (including unset) is off.
    """
    return os.environ.get(RECEIVER_SLI_EMF_FLAG_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def emit_receiver_sli_emf(
    entity_type: str,
    success: bool,
    serving_stale_total: float,
) -> None:
    """Emit one receiver-SLI EMF line to stdout (additive, fire-and-forget).

    Writes a single Embedded Metric Format JSON document carrying the per-arm
    outcome CONSTITUENTS (success / server_error increments) AND the co-required
    ``ServingStaleTotal`` in the SAME document. The success rate is intentionally
    NOT emitted: it is derived downstream as
    ``Sum(Success)/(Sum(Success)+Sum(ServerError))`` so there is no temporal or
    structural seam at which a flattered rate can be read without the stale
    context (TDD §"Honoring the co-read PROHIBITION"; mirrors
    ``success_rate_with_stale_context`` at the export boundary).

    No-ops unless ``RECEIVER_SLI_EMF_ENABLED`` is set (ship-dark default).

    Fire-and-forget: any failure (serialization, stdout) is swallowed and
    best-effort logged at debug; this function NEVER raises and NEVER blocks the
    request hot path (this module's line-7 in-memory/no-synchronous-I/O contract).

    Args:
        entity_type: Body-parameterized arm ("project" | "section") — the EMF
            ``arm`` dimension.
        success: True on 2xx; False on 5xx. Maps to exactly one of the two
            outcome constituents (success XOR server_error == 1).
        serving_stale_total: Fleet-wide LKG-serve count co-emitted in the same
            document. Sourced by the caller via ``_serving_stale_total_value()``
            (the same path ``success_rate_with_stale_context`` uses) so the
            co-read is structurally inseparable.
    """
    if not _receiver_sli_emf_enabled():
        return
    try:
        success_count = 1 if success else 0
        server_error_count = 0 if success else 1
        document = {
            "_aws": {
                "Timestamp": int(time.time() * 1000),
                "CloudWatchMetrics": [
                    {
                        "Namespace": RECEIVER_SLI_EMF_NAMESPACE,
                        "Dimensions": [["arm"]],
                        "Metrics": [
                            {"Name": "ReceiverQueryOutcomeSuccess", "Unit": "Count"},
                            {"Name": "ReceiverQueryOutcomeServerError", "Unit": "Count"},
                            # CO-READ ENFORCEMENT: ServingStaleTotal is emitted in
                            # the SAME document as the outcome constituents so the
                            # success rate can never be read without stale context.
                            {"Name": "ServingStaleTotal", "Unit": "Count"},
                        ],
                    }
                ],
            },
            "arm": entity_type,
            "ReceiverQueryOutcomeSuccess": success_count,
            "ReceiverQueryOutcomeServerError": server_error_count,
            "ServingStaleTotal": serving_stale_total,
        }
        # One newline-terminated JSON line to stdout (NOT print(): keeps the
        # T201 lint surface clean and matches the EMF "one document per line"
        # log-driver contract). stdout already carries structured logs; the EMF
        # line joins the same stream under the existing log-sink trust boundary.
        sys.stdout.write(json.dumps(document) + "\n")
    except Exception:  # noqa: BLE001 -- fire-and-forget: emit must never raise/block the hot path
        # Best-effort debug only, acquired lazily (NOT module-scope) to avoid the
        # premature SDK auto-config footgun guarded by core.logging.reset_logging.
        try:
            from autom8_asana.core.logging import get_logger

            get_logger(__name__).debug("receiver_sli_emf_emit_failed", exc_info=True)
        except Exception:  # noqa: BLE001 -- logging must never resurrect the swallowed error
            pass


def record_query_fallback_cause(entity_type: str, cause: str) -> None:
    """Record one disaggregated S7 fallback cause (S7-GATE-FIDELITY).

    The receiver-side companion to ``record_receiver_query_outcome``: it splits
    the outcome by the THREE causes the consumer ``GetDfFallback`` collapses into
    one counter, so the S7 fallback-retirement verdict can read CAUSE.

    Both recorders are called on the same request: the binary
    ``RECEIVER_QUERY_OUTCOME`` (the deploy-gate SLI denominator) AND this
    per-cause counter. ``honest_refusal`` is a 2xx (it does NOT decrement the SLI
    success count); ``cadence_503`` and ``capacity_502`` are 5xx (they ARE the
    server_error split). ``data_2xx`` marks a real-data success so honest_refusal
    can be read against it (the liveness-masquerade defeat).

    Args:
        entity_type: Body-parameterized arm ("project" | "section").
        cause: One of ``S7_CAUSE_CADENCE_503`` / ``S7_CAUSE_CAPACITY_502`` /
            ``S7_CAUSE_HONEST_REFUSAL`` / ``S7_OUTCOME_DATA_2XX``. An unrecognized
            value is accepted as-is (low cardinality; the caller derives it from a
            closed set) so the recorder never raises on the fire-and-forget path.
    """
    RECEIVER_QUERY_FALLBACK_CAUSE.labels(entity_type=entity_type, cause=cause).inc()


def receiver_fallback_cause_counts(
    entity_type: str | None = None,
) -> dict[str, float]:
    """Return the disaggregated S7 cause counts (the verdict-reads-cause accessor).

    The S7 fallback-retirement verdict reads this instead of inferring cause from
    the collapsed success/server_error split. Returns a dict keyed by cause
    (cadence_503 / capacity_502 / honest_refusal / data_2xx), each defaulting to
    0.0 so a verdict never trips on a missing key.

    Args:
        entity_type: When given, restrict to one arm ("project" | "section");
            None aggregates across arms.

    Returns:
        ``{cause: count}`` for every known cause, including data_2xx, with absent
        causes reported as 0.0.
    """
    counts: dict[str, float] = {
        S7_CAUSE_CADENCE_503: 0.0,
        S7_CAUSE_CAPACITY_502: 0.0,
        S7_CAUSE_HONEST_REFUSAL: 0.0,
        S7_OUTCOME_DATA_2XX: 0.0,
    }
    for metric in RECEIVER_QUERY_FALLBACK_CAUSE.collect():
        for sample in metric.samples:
            if not sample.name.endswith("_total"):
                continue
            if entity_type is not None and sample.labels.get("entity_type") != entity_type:
                continue
            cause = sample.labels.get("cause", "")
            if cause in counts:
                counts[cause] += sample.value
    return counts


# --- TD-007 honest observability instrumentation (observability-plan §2) ---
# Receiver-EMITTED signals only: the leading indicators the receiver process can
# observe about the CPU-on-event-loop starvation failure that TD-001 fixes.
# External CloudWatch/ALB signals (alb_unhealthy_host_count, ecs_task_replacement_count,
# elb_502_rate) are the re-gate stream's to correlate — NOT emitted here. All
# emission is in-memory and cheap; the event-loop-lag monitor samples on a slow
# (5s) timer off the request hot path, and per-request paths only do counter/
# histogram increments. See dataframes/concurrency.py for the semaphore gate.

# §1.2 — Event-loop lag. The LEADING indicator of CPU-on-loop starvation: when a
# Polars merge runs on the loop thread, the loop cannot service its own timer, so
# the measured sleep overshoot (actual - intended) spikes. Histogram so p50/p99
# are derivable (the design asks for p50/p99). Seconds (not ms) per Prometheus
# base-unit convention; the design's `event_loop_lag_ms` is the same signal.
EVENT_LOOP_LAG_SECONDS = Histogram(
    "autom8y_asana_event_loop_lag_seconds",
    "Asyncio event-loop scheduling lag (measured sleep overshoot); leading "
    "indicator of CPU-on-loop starvation (TD-001 failure mode)",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# §1.2 — CPU-thread offload semaphore occupancy. in_use = slots held; waiting =
# coroutines blocked on acquire (saturation depth); max = configured cap. Three
# gauges so a dashboard can show "offload gate saturation" directly. Sourced from
# the single shared gate in dataframes/concurrency.py:run_cpu_bound.
CPU_THREAD_SEMAPHORE_IN_USE = Gauge(
    "autom8y_asana_cpu_thread_semaphore_in_use",
    "CPU-bound offload semaphore slots currently held (in-flight to_thread merges)",
)
CPU_THREAD_SEMAPHORE_WAITING = Gauge(
    "autom8y_asana_cpu_thread_semaphore_waiting",
    "Coroutines currently blocked waiting to acquire the CPU-thread offload gate",
)
CPU_THREAD_SEMAPHORE_MAX = Gauge(
    "autom8y_asana_cpu_thread_semaphore_max",
    "Configured CPU-thread offload semaphore capacity (cpu_thread_concurrency)",
)

# §1.3 — LKG serving honesty. serving_stale_total makes the LKG-flattering of the
# success rate VISIBLE (the design's PROHIBITION: success_rate must not be read
# without this co-available). lkg_serve_age is the age of the stale frame served.
SERVING_STALE_TOTAL = Counter(
    "autom8y_asana_serving_stale_total",
    "LKG (stale-but-within-ceiling) frames served as 2xx, per entity type. "
    "Co-required for honest reading of the success rate (observability-plan §2 PROHIBITION)",
    labelnames=["entity_type"],
)
LKG_SERVE_AGE_SECONDS = Histogram(
    "autom8y_asana_lkg_serve_age_seconds",
    "Age (seconds) of the LKG frame served on the stale-serve path",
    labelnames=["entity_type"],
    buckets=(60, 180, 300, 600, 900, 1800, 3000, 7200, 36000),
)


def record_event_loop_lag(lag_seconds: float) -> None:
    """Observe one event-loop lag sample (TD-007, observability-plan §1.2).

    Emitted by the EventLoopLagMonitor on its slow sample timer — NOT on any
    request hot path. ``lag_seconds`` is the measured overshoot of a known sleep
    interval (actual_elapsed - intended); negative jitter is clamped to 0.
    """
    EVENT_LOOP_LAG_SECONDS.observe(max(0.0, lag_seconds))


def record_cpu_thread_semaphore(in_use: int, waiting: int, max_slots: int) -> None:
    """Update the CPU-thread offload semaphore gauges (TD-007, §1.2).

    Called from the concurrency gate on each acquire/release. Pure gauge sets;
    no allocation, no I/O — safe on the offload path.

    Args:
        in_use: Slots currently held (in-flight CPU-bound to_thread submissions).
        waiting: Coroutines blocked on acquire (offload-gate saturation depth).
        max_slots: Configured capacity (cpu_thread_concurrency).
    """
    CPU_THREAD_SEMAPHORE_IN_USE.set(in_use)
    CPU_THREAD_SEMAPHORE_WAITING.set(waiting)
    CPU_THREAD_SEMAPHORE_MAX.set(max_slots)


def record_serving_stale(entity_type: str, age_seconds: float) -> None:
    """Record one LKG (stale-within-ceiling) 2xx serve (TD-007, §1.3).

    Emitted from the dataframe_cache LKG path (dataframe_cache.py:531-554) so the
    flattering of the success rate by stale 2xx is observable. Pairs the count
    with the served frame's age.

    Args:
        entity_type: Entity type of the stale frame (e.g., "offer", "project").
        age_seconds: Age of the served LKG frame at serve time.
    """
    SERVING_STALE_TOTAL.labels(entity_type=entity_type).inc()
    LKG_SERVE_AGE_SECONDS.labels(entity_type=entity_type).observe(max(0.0, age_seconds))


def receiver_query_success_rate(entity_type: str | None = None) -> float | None:
    """Compute the receiver-emitted honest success rate (TD-007, §2.1).

    success_rate = 2xx / (2xx + 5xx), from the receiver-side RECEIVER_QUERY_OUTCOME
    counters (NOT ALB-inferred). With ``entity_type`` None, returns the COMBINED
    rate across arms; otherwise the per-arm rate ("project" | "section").

    PROHIBITION (observability-plan §2): this rate MUST NOT be read as an SLO
    without ``serving_stale_total`` co-available — a rate computed while stale
    frames are served as 2xx is flattered. Callers/dashboards reading this MUST
    also surface ``SERVING_STALE_TOTAL``; ``success_rate_with_stale_context``
    enforces that co-availability programmatically.

    Returns:
        The success rate in [0.0, 1.0], or None when no requests have been
        recorded (denominator 0 — avoid reporting a fabricated 100%).
    """
    success = 0.0
    server_error = 0.0
    for metric in RECEIVER_QUERY_OUTCOME.collect():
        for sample in metric.samples:
            if not sample.name.endswith("_total"):
                continue
            if entity_type is not None and sample.labels.get("entity_type") != entity_type:
                continue
            if sample.labels.get("outcome") == "success":
                success += sample.value
            elif sample.labels.get("outcome") == "server_error":
                server_error += sample.value
    denom = success + server_error
    if denom == 0:
        return None
    return success / denom


def _serving_stale_total_value() -> float:
    """Sum SERVING_STALE_TOTAL across entity types (co-availability probe)."""
    total = 0.0
    for metric in SERVING_STALE_TOTAL.collect():
        for sample in metric.samples:
            if sample.name.endswith("_total"):
                total += sample.value
    return total


def success_rate_with_stale_context(
    entity_type: str | None = None,
) -> tuple[float | None, float]:
    """Return (success_rate, serving_stale_total) as ONE inseparable reading.

    Enforces the observability-plan §2 PROHIBITION structurally: the honest
    success rate is NEVER returned without its co-required stale context, so a
    caller cannot read a flattered rate in isolation. Dashboards/gates MUST use
    this accessor (not bare ``receiver_query_success_rate``) when reporting the SLO.

    Returns:
        ``(success_rate, serving_stale_total)`` where success_rate is None on a
        zero denominator. The second element is the fleet-wide stale-serve count
        that contextualizes how flattered the rate may be.
    """
    return receiver_query_success_rate(entity_type), _serving_stale_total_value()


# §2.2 — CPU_STARVATION_REPLACEMENT correlation precondition (receiver-observable
# subset). The design classifies a 5xx cluster as CPU_STARVATION_REPLACEMENT when
# four signals correlate; two are RECEIVER-observable (event-loop lag spike + CPU
# semaphore saturation) and two are EXTERNAL (alb_unhealthy_host_count,
# ecs_task_replacement_count) which the re-gate stream correlates from CloudWatch.
# This helper evaluates the RECEIVER-side precondition: when it fires, the receiver
# has contributed the two leading signals; the re-gate confirms the external two.
EVENT_LOOP_LAG_STARVATION_THRESHOLD_SECONDS = 0.5  # §2.2: >500ms lag spike


def cpu_starvation_precondition(
    event_loop_lag_seconds: float,
    cpu_thread_semaphore_waiting: int,
) -> bool:
    """Evaluate the receiver-side CPU_STARVATION_REPLACEMENT precondition (§2.2).

    Fires when BOTH receiver-observable leading signals are present:
      1. event-loop lag exceeded the 500ms starvation threshold, AND
      2. the CPU-thread offload gate had waiters (semaphore saturated).

    A True return is the receiver's contribution to the four-signal correlation;
    the re-gate stream confirms the two external signals (alb_unhealthy_host_count
    rising + ecs_task_replacement_count increment) from CloudWatch before
    declaring a confirmed CPU_STARVATION_REPLACEMENT event. This function does NOT
    self-declare the full classification (the two external signals are out of the
    receiver's observability).

    Args:
        event_loop_lag_seconds: Observed event-loop lag in the window.
        cpu_thread_semaphore_waiting: Observed offload-gate waiter count in the window.

    Returns:
        True when both receiver-side preconditions hold.
    """
    return (
        event_loop_lag_seconds > EVENT_LOOP_LAG_STARVATION_THRESHOLD_SECONDS
        and cpu_thread_semaphore_waiting > 0
    )


# --- OBS-EXPORTS-001 exports-route metrics (SRE OB2 sprint) ---
# Per .know/obs.md OBS-EXPORTS-001 symptom list. These emit from the
# ``export_handler`` request span seam (api/routes/exports.py), reusing the OB2
# span locals (row_count_pre_dedup, row_count_post_dedup, identity_suppressed_count,
# default_section_applied, date_filter_expr, entity_type, format) plus an additive
# time.perf_counter() duration read. Emission is ADDITIVE — no pipeline step,
# helper, or engine surface is altered. SLO targets + burn-rate alert rules live
# in the autom8y MONOREPO Terraform (asana has 0 .tf) and are OUT of scope here.
#
# Boolean labels are stringified "true"/"false" per Prometheus convention (low
# cardinality; date_filter_applied / section_default_applied are bool seam reads).

# Latency SLI substrate — per-request handler duration, labeled by entity_type
# and format. Histogram so server-side p50/p95/p99 are derivable (averages are
# never valid for latency monitoring). Buckets span sub-second hot path through
# the multi-project / large-export tail.
EXPORTS_REQUEST_DURATION = Histogram(
    "autom8y_asana_exports_request_duration_seconds",
    "End-to-end export_handler duration (entity validation through serialization)",
    labelnames=["entity_type", "format"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

# Predicate-split traffic + outcome shape. One increment per successful export,
# labeled by whether the date-op split produced a filter and whether the
# ACTIVE-default section was injected. Drives the "what shape of request are we
# serving?" panel without recomputing anything (labels are the existing seam
# locals already written as span attributes).
EXPORTS_PREDICATE_SPLIT_OUTCOME = Counter(
    "autom8y_asana_exports_predicate_split_outcome_total",
    "Successful exports split by date-filter-applied and section-default-applied",
    labelnames=["entity_type", "date_filter_applied", "section_default_applied"],
)

# Identity-suppression volume. Counter incremented by the per-request suppressed
# row count (identity_suppressed_count) so operators can see how many rows the
# null-key suppression removed across the fleet, per entity arm.
EXPORTS_IDENTITY_ROWS_SUPPRESSED = Counter(
    "autom8y_asana_exports_identity_rows_suppressed_total",
    "Rows removed by null-identity suppression (include_incomplete_identity=False)",
    labelnames=["entity_type"],
)

# Pre/post-dedup row distribution. Two observe() calls per request labeled
# stage=pre_dedup / stage=post_dedup — the OBS-EXPORTS-001 symptom-list pre/post
# rows histogram. Bucket boundaries span single-row through large multi-project
# account-grain exports.
EXPORTS_ROWS = Histogram(
    "autom8y_asana_exports_rows",
    "Export row counts observed pre- and post-dedup (stage label distinguishes)",
    labelnames=["entity_type", "stage"],
    buckets=(1, 10, 50, 100, 500, 1000, 5000, 10000, 50000),
)

# NOTE — exports_format_negotiation_fallback_total is DROPPED per the approved
# contract (in_scope=false). No format-fallback seam exists: ``_format_dataframe_response``
# branches deterministically on the Pydantic-validated Literal["json","csv","parquet"]
# selector, and export_handler passes accept=None so the content-negotiation branch
# is never reached. served_format always equals requested_format; emitting it would
# fabricate a vanity metric with no real source seam (vanity-metrics anti-pattern).


def record_exports_request_duration(
    entity_type: str,
    export_format: str,
    duration_seconds: float,
) -> None:
    """Observe one export_handler request duration.

    Args:
        entity_type: ``request_body.entity_type``.
        export_format: ``request_body.format`` (json | csv | parquet).
        duration_seconds: ``time.perf_counter()`` delta across the handler body.
    """
    EXPORTS_REQUEST_DURATION.labels(
        entity_type=entity_type,
        format=export_format,
    ).observe(duration_seconds)


def record_exports_predicate_split(
    entity_type: str,
    *,
    date_filter_applied: bool,
    section_default_applied: bool,
) -> None:
    """Record a successful export's predicate-split outcome shape.

    Bool labels are stringified lowercase ("true"/"false") per Prometheus
    convention. Values are the existing handler-space seam locals (already
    written as OB2 span attributes); nothing is recomputed.
    """
    EXPORTS_PREDICATE_SPLIT_OUTCOME.labels(
        entity_type=entity_type,
        date_filter_applied=str(date_filter_applied).lower(),
        section_default_applied=str(section_default_applied).lower(),
    ).inc()


def record_exports_identity_rows_suppressed(
    entity_type: str,
    suppressed_count: int,
) -> None:
    """Increment the identity-suppressed-rows counter by ``suppressed_count``.

    Args:
        entity_type: ``request_body.entity_type``.
        suppressed_count: ``identity_suppressed_count`` (height_pre - height_post
            of the unchanged ``filter_incomplete_identity`` call). A zero count
            is a no-op increment.
    """
    EXPORTS_IDENTITY_ROWS_SUPPRESSED.labels(entity_type=entity_type).inc(suppressed_count)


def record_exports_rows(
    entity_type: str,
    row_count_pre_dedup: int,
    row_count_post_dedup: int,
) -> None:
    """Observe pre- and post-dedup row counts for one export.

    Emits two observations labeled ``stage=pre_dedup`` / ``stage=post_dedup`` from
    the existing OB2 span locals (``row_count_pre_dedup`` / ``row_count_post_dedup``).
    """
    EXPORTS_ROWS.labels(entity_type=entity_type, stage="pre_dedup").observe(row_count_pre_dedup)
    EXPORTS_ROWS.labels(entity_type=entity_type, stage="post_dedup").observe(row_count_post_dedup)


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
