"""Metrics emission for DataServiceClient.

Private module extracted from client.py to separate metrics concerns from
the main client class. Functions are module-level to enable independent
testing and reduce class surface area.

These functions are NOT part of the public API -- they are imported and
used by DataServiceClient internally.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autom8_asana.protocols.log import LogProvider

# Type alias for metrics hook callback
# Signature: (name: str, value: float, tags: dict[str, str]) -> None
MetricsHook = Callable[[str, float, dict[str, str]], None]


def emit_metric(
    hook: MetricsHook | None,
    name: str,
    value: float,
    tags: dict[str, str],
    log: LogProvider | Any | None,
) -> None:
    """Emit a metric via the configured metrics hook.

    Generic function for emitting metrics.
    Failures are logged but don't break requests (graceful degradation).

    Args:
        hook: Metrics hook callback, or None if metrics disabled.
        name: Metric name (e.g., "insights_request_total").
        value: Metric value (count=1 for counters, duration for histograms).
        tags: Metric tags/labels for dimensionality.
        log: Logger instance for structured logging.
    """
    if hook is None:
        return

    try:
        hook(name, value, tags)
    except (TypeError, ValueError, RuntimeError, OSError) as e:
        # Graceful degradation: metrics failures don't break requests
        if log:
            log.warning(
                f"DataServiceClient: Failed to emit metric {name}: {e}",
                extra={"metric_name": name, "tags": tags},
            )
