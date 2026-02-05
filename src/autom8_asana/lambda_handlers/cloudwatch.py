"""Shared CloudWatch metric emission for Lambda handlers.

Provides a reusable emit_metric() function used by both
cache_warmer.py and cache_invalidate.py.

Per TDD-SDK-ALIGNMENT Path 3: Extracted from cache_warmer.py to avoid
code duplication across Lambda handlers.
"""

from __future__ import annotations

import os
from typing import Any

from autom8y_log import get_logger

logger = get_logger(__name__)

CLOUDWATCH_NAMESPACE = os.environ.get("CLOUDWATCH_NAMESPACE", "autom8/lambda")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "staging")

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
        namespace: Override namespace (defaults to CLOUDWATCH_NAMESPACE).
    """
    client = _get_cloudwatch_client()
    ns = namespace or CLOUDWATCH_NAMESPACE

    metric_dimensions = [
        {"Name": "environment", "Value": ENVIRONMENT},
    ]
    if dimensions:
        for dim_name, dim_value in dimensions.items():
            metric_dimensions.append({"Name": dim_name, "Value": dim_value})

    try:
        client.put_metric_data(
            Namespace=ns,
            MetricData=[{
                "MetricName": metric_name,
                "Value": value,
                "Unit": unit,
                "Dimensions": metric_dimensions,
            }],
        )
    except Exception as e:  # BROAD-CATCH: metrics -- CloudWatch metric emission must not fail the handler
        logger.warning(
            "metric_emit_error",
            extra={"metric": metric_name, "error": str(e)},
        )
