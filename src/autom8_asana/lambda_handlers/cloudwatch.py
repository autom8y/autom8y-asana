"""Shared CloudWatch metric emission for Lambda handlers.

Provides a reusable emit_metric() function used by both
cache_warmer.py and cache_invalidate.py.

Per TDD-SDK-ALIGNMENT Path 3: Extracted from cache_warmer.py to avoid
code duplication across Lambda handlers.
"""

from __future__ import annotations

from typing import Any

from autom8y_log import get_logger

logger = get_logger(__name__)

_cloudwatch_client: Any = None


def _get_cloudwatch_client() -> Any:
    """Lazily initialize CloudWatch client."""
    global _cloudwatch_client
    if _cloudwatch_client is None:
        import boto3

        _cloudwatch_client = boto3.client("cloudwatch")
    return _cloudwatch_client


def emit_metric(
    metric_name: str,
    value: float,
    unit: str = "Count",
    dimensions: dict[str, str] | None = None,
    namespace: str | None = None,
) -> None:
    """Emit CloudWatch metric with graceful degradation.

    Args:
        metric_name: Name of the metric.
        value: Metric value.
        unit: CloudWatch unit (Count, Milliseconds, etc.).
        dimensions: Optional additional dimensions.
        namespace: Override namespace (defaults to settings.observability.cloudwatch_namespace).
    """
    from autom8_asana.settings import get_settings

    obs = get_settings().observability
    client = _get_cloudwatch_client()
    ns = namespace or obs.cloudwatch_namespace

    metric_dimensions = [
        {"Name": "environment", "Value": obs.environment},
    ]
    if dimensions:
        for dim_name, dim_value in dimensions.items():
            metric_dimensions.append({"Name": dim_name, "Value": dim_value})

    try:
        client.put_metric_data(
            Namespace=ns,
            MetricData=[
                {
                    "MetricName": metric_name,
                    "Value": value,
                    "Unit": unit,
                    "Dimensions": metric_dimensions,
                }
            ],
        )
    except (
        Exception  # noqa: BLE001
    ) as e:  # BROAD-CATCH: metrics -- CloudWatch metric emission must not fail the handler
        logger.warning(
            "metric_emit_error",
            extra={"metric": metric_name, "error": str(e)},
        )


def emit_warmer_coverage_rate(keys_completed: int, total_enumerated: int) -> float:
    """Emit the warmer coverage rate (TD-005, ties to TD-007 honesty theme).

    ``warmer_coverage_rate = keys_completed / total_enumerated`` makes the
    pre-materialization coverage observable: a value < 1.0 means some of the
    enumerated bulk keys were NOT warmed before the consumer batch, so the
    receiver will cold-build (and 503) those keys. Like TD-007's honest
    success rate, a zero denominator returns 0.0 rather than a fabricated
    100% -- "nothing enumerated" is not "fully covered".

    Emitted as a CloudWatch ``Percent`` metric (0-100) so it is dashboardable
    alongside the warmer's other ``emit_metric`` signals.

    Args:
        keys_completed: Count of ``(project_gid, entity_type)`` keys warmed.
        total_enumerated: Total keys the warm cycle set out to cover.

    Returns:
        The coverage rate in [0.0, 1.0] (0.0 when ``total_enumerated == 0``).
    """
    rate = (keys_completed / total_enumerated) if total_enumerated > 0 else 0.0
    emit_metric("WarmerCoverageRate", rate * 100.0, unit="Percent")
    return rate
