"""CloudWatch metric emission for the freshness probe CLI.

Implements HANDOFF §1 work-item-4 (Batch-B): emit five CLI metrics to
the Pascal-cased namespace `Autom8y/FreshnessProbe`, batched into a
single `put_metric_data` call per ADR-006 §Decision (atomic emission
timestamp + cross-metric correlation).

The five CLI metrics:
- ``MaxParquetAgeSeconds``      (alarmed; from FreshnessReport.max_age_seconds)
- ``ForceWarmLatencySeconds``   (latency only — no alarm; FLAG-1 boundary)
- ``SectionCount``              (cardinality observation; from FreshnessReport.parquet_count)
- ``SectionAgeP95Seconds``      (distribution-aware; from FreshnessReport.section_age_p95_seconds())
- ``SectionCoverageDelta``      (informational only — NO ALARM per PRD §6 C-6 / ADR-006)

C-6 HARD CONSTRAINT (ADR-006 alarm-vs-metric matrix):
    SectionCoverageDelta MUST NOT be wired to any CloudWatch alarm. This module
    enforces the constraint mechanically: ``ALARMED_METRICS`` is a frozenset
    that excludes ``SectionCoverageDelta`` and includes ONLY metrics whose
    emission an alarm may legitimately consume. Callers wiring alarms MUST
    consult ``ALARMED_METRICS`` before declaring an alarm; ``c6_guard_check``
    raises ``C6ConstraintViolation`` when an alarm wiring path attempts to
    target a non-alarmed metric. See PRD `verify-active-mrr-provenance.prd.md`
    §6 C-6 + ADR-006 alarm-vs-metric matrix.

The coalescer-side metric ``CoalescerDedupCount`` lives at the lowercase
namespace `autom8y/cache-warmer` per ADR-006 §Decision (joins existing warmer
runtime namespace). It is emitted from
``autom8_asana.cache.dataframe.coalescer``, NOT from this module.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autom8_asana.metrics.freshness import FreshnessReport

# CLI freshness probe namespace (Pascal — per ADR-006 namespace assignment table).
FRESHNESS_PROBE_NAMESPACE: str = "Autom8y/FreshnessProbe"

# Metric names — frozen string constants so callers cannot accidentally drift.
METRIC_MAX_PARQUET_AGE_SECONDS: str = "MaxParquetAgeSeconds"
METRIC_FORCE_WARM_LATENCY_SECONDS: str = "ForceWarmLatencySeconds"
METRIC_SECTION_COUNT: str = "SectionCount"
METRIC_SECTION_AGE_P95_SECONDS: str = "SectionAgeP95Seconds"
METRIC_SECTION_COVERAGE_DELTA: str = "SectionCoverageDelta"

# All five CLI metric names (the ADR-006 single-batch set).
ALL_CLI_METRICS: frozenset[str] = frozenset(
    {
        METRIC_MAX_PARQUET_AGE_SECONDS,
        METRIC_FORCE_WARM_LATENCY_SECONDS,
        METRIC_SECTION_COUNT,
        METRIC_SECTION_AGE_P95_SECONDS,
        METRIC_SECTION_COVERAGE_DELTA,
    }
)

# Metrics that an alarm MAY legitimately consume. ``SectionCoverageDelta`` is
# DELIBERATELY EXCLUDED per PRD §6 C-6 and ADR-006 alarm-vs-metric matrix
# row "SectionCoverageDelta | NO — HARD CONSTRAINT".
#
# In ADR-006's matrix, only ``MaxParquetAgeSeconds`` carries alarms (ALERT-1 +
# ALERT-2). The other CLI metrics are emitted but unalarmed at the freshness
# probe altitude. We list them all here as "alarmable in principle" for future
# extensibility, but only ``MaxParquetAgeSeconds`` has an alarm wired today.
ALARMED_METRICS: frozenset[str] = frozenset(
    {
        METRIC_MAX_PARQUET_AGE_SECONDS,
        METRIC_FORCE_WARM_LATENCY_SECONDS,
        METRIC_SECTION_COUNT,
        METRIC_SECTION_AGE_P95_SECONDS,
    }
)


class C6ConstraintViolation(RuntimeError):
    """Raised when alarm-wiring code attempts to target SectionCoverageDelta.

    PRD §6 C-6 declares "EMPTY SECTIONS ARE NOT A FAILURE SIGNAL." The
    SectionCoverageDelta metric is informational only; wiring an alarm on it is
    a specification violation, not an oversight. ADR-006's alarm-vs-metric
    matrix elevates the prohibition to a hard contract.
    """


def c6_guard_check(metric_name: str) -> None:
    """Raise C6ConstraintViolation iff ``metric_name`` is forbidden from alarms.

    Call this at any code site that wires a CloudWatch alarm to a metric
    name that originates from this module. The check is mechanical: it
    operates on the closed enumeration ``ALL_CLI_METRICS`` minus
    ``ALARMED_METRICS``.

    Raises:
        C6ConstraintViolation: when ``metric_name`` is in
            ``ALL_CLI_METRICS - ALARMED_METRICS``. Currently this is exactly
            ``{SectionCoverageDelta}``.
    """
    if metric_name in ALL_CLI_METRICS and metric_name not in ALARMED_METRICS:
        raise C6ConstraintViolation(
            f"PRD §6 C-6 / ADR-006: metric '{metric_name}' MUST NOT be wired to "
            "any CloudWatch alarm. SectionCoverageDelta is informational only — "
            "an empty section is by-design state, not a failure signal."
        )


def _get_cloudwatch_client() -> Any:
    """Return a boto3 CloudWatch client.

    Lazy import keeps this module importable when boto3 is unavailable.
    """
    import boto3

    region = os.environ.get("AWS_REGION") or os.environ.get("ASANA_CACHE_S3_REGION", "us-east-1")
    return boto3.client("cloudwatch", region_name=region)


def emit_freshness_probe_metrics(
    *,
    report: FreshnessReport,
    metric_name_dim: str,
    project_gid: str,
    section_coverage_delta: int,
    force_warm_latency_seconds: float | None = None,
    section_age_p95_seconds: int | None = None,
    cw_client: Any | None = None,
) -> dict[str, Any]:
    """Emit the five CLI freshness-probe metrics in a single batched call.

    Per ADR-006 §Decision: the five CLI metrics SHARE one ``put_metric_data``
    call so they share an emission timestamp (load-bearing for cross-metric
    correlation, e.g., joining MaxParquetAgeSeconds with SectionCount for a
    per-invocation density curve).

    ``ForceWarmLatencySeconds`` is emitted iff ``force_warm_latency_seconds``
    is not None — only the ``--force-warm --wait`` success path supplies a
    measurable end-to-end window per the FLAG-1 boundary. Default async path
    omits this metric (no end timestamp available within a single CLI process).

    Best-effort: failure is logged via stderr but never blocks the caller.
    Mirrors the autom8y_telemetry CW emission pattern.

    Args:
        report: FreshnessReport supplying MaxParquetAgeSeconds + SectionCount
            (+ optional SectionAgeP95Seconds via report.section_age_p95_seconds()
            when section_age_p95_seconds is not pre-computed by the caller).
        metric_name_dim: Dimension value identifying the CLI metric being
            probed (e.g., "active_mrr") for cross-metric attribution.
        project_gid: Dimension value identifying the project under probe.
        section_coverage_delta: classifier_active_section_count - parquet_count.
            Positive = empty sections (expected per C-6). NO ALARM consumes this.
        force_warm_latency_seconds: FLAG-1-bounded end-to-end latency when
            available; None on default (async) path. The flag-parse-to-fresh-state
            window MUST include any coalescer wait time per FLAG-1 boundary.
        section_age_p95_seconds: Pre-computed P95 from
            ``report.section_age_p95_seconds(now=...)``. When None, this method
            invokes ``report.section_age_p95_seconds()`` with default ``now``.
        cw_client: Override CloudWatch client; injectable for unit tests.

    Returns:
        Diagnostic dict with the metric data list that was sent. Suitable for
        test assertions and post-emission logging.
    """
    if cw_client is None:
        cw_client = _get_cloudwatch_client()

    # Compute P95 if caller did not supply it.
    if section_age_p95_seconds is None:
        section_age_p95_seconds = report.section_age_p95_seconds()

    dimensions = [
        {"Name": "metric_name", "Value": metric_name_dim},
        {"Name": "project_gid", "Value": project_gid},
    ]

    metric_data: list[dict[str, Any]] = [
        {
            "MetricName": METRIC_MAX_PARQUET_AGE_SECONDS,
            "Value": float(report.max_age_seconds),
            "Unit": "Seconds",
            "Dimensions": dimensions,
        },
        {
            "MetricName": METRIC_SECTION_COUNT,
            "Value": float(report.parquet_count),
            "Unit": "Count",
            "Dimensions": dimensions,
        },
        {
            "MetricName": METRIC_SECTION_AGE_P95_SECONDS,
            "Value": float(section_age_p95_seconds),
            "Unit": "Seconds",
            "Dimensions": dimensions,
        },
        # SectionCoverageDelta — informational only. C-6 HARD CONSTRAINT (NO ALARM).
        # See ADR-006 alarm-vs-metric matrix; c6_guard_check enforces mechanically.
        {
            "MetricName": METRIC_SECTION_COVERAGE_DELTA,
            "Value": float(section_coverage_delta),
            "Unit": "Count",
            "Dimensions": dimensions,
        },
    ]
    if force_warm_latency_seconds is not None:
        metric_data.append(
            {
                "MetricName": METRIC_FORCE_WARM_LATENCY_SECONDS,
                "Value": float(force_warm_latency_seconds),
                "Unit": "Seconds",
                "Dimensions": dimensions,
            },
        )

    try:
        cw_client.put_metric_data(
            Namespace=FRESHNESS_PROBE_NAMESPACE,
            MetricData=metric_data,
        )
    except Exception as exc:  # noqa: BLE001 — best-effort metric emission
        # Never block the CLI on a CloudWatch failure (PRD C-2 backwards-compat:
        # default-mode CLI MUST NOT change exit code semantics from added
        # observability emissions). Surface via stderr so the caller (the CLI)
        # observes the warning without changing exit code.
        import sys

        sys.stderr.write(
            f"WARNING: CloudWatch metric emission failed: {exc!r} "
            f"(namespace={FRESHNESS_PROBE_NAMESPACE})\n"
        )

    return {"namespace": FRESHNESS_PROBE_NAMESPACE, "metric_data": metric_data}
