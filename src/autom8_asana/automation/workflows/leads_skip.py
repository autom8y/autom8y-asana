"""The 4-class emitted skip taxonomy (WS-SKIP) for the leads consumer.

Per HANDOFF §4 / ADR grain-bridge D5: every refusal on the per-business leads
path EMITs (log + metric + skipped-count). NEVER a silent drop; NEVER a fleet
fallback. The skip class enum is the binding CLOSED 4-class taxonomy; the
read-vs-mint and input-state distinctions are carried in ``sub_reason`` (EC-1 /
EC-7 discriminability).

PII discipline (SC-BUILD / SCAR-028): office_phone is masked via
``mask_phone_number`` before it touches a log line or a metric label -- never
raw E.164.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import TYPE_CHECKING

from autom8_asana.clients.utils.pii import mask_phone_number

if TYPE_CHECKING:
    from autom8y_log import LoggerProtocol

#: Metrics hook signature: (name, value, labels) -> None. Mirrors the
#: data-client ``MetricsHook`` convention so the consumer is harness-agnostic
#: (Prometheus / CloudWatch / DataDog adapters all satisfy it).
MetricsHook = Callable[[str, float, dict[str, str]], None]

#: Counter metric name for emitted skips.
SKIP_METRIC_NAME = "grain_bridge_leads_skipped_total"


class SkipClass(StrEnum):
    """The binding CLOSED 4-class skip taxonomy (WS-SKIP)."""

    RESOLUTION_MISS = "resolution_miss"
    COLLISION_CONFLICT = "collision_conflict"
    INACTIVE_OR_EMPTY = "inactive_or_empty"
    MINT_UNAVAILABLE = "mint_unavailable"


def emit_skip(
    log: LoggerProtocol,
    metrics_hook: MetricsHook | None,
    *,
    klass: SkipClass,
    office_phone: str,
    sub_reason: str | None = None,
) -> None:
    """Emit a skip signal: structured log + metric counter.

    The caller is responsible for incrementing its own per-class skipped count
    (the reconciliation invariant ``attempted == succeeded + Sum(skips)``).

    Args:
        log: structured logger (LogProvider).
        metrics_hook: optional metric sink ``(name, value, labels)``.
        klass: the skip class (one of the CLOSED 4).
        office_phone: the read key -- masked before emission (never raw E.164).
        sub_reason: optional discriminator (e.g. ``server_404``, ``input_null``,
            ``rate_limited``, ``read_5xx``).
    """
    masked = mask_phone_number(office_phone)
    log.warning(
        klass.value,
        office_phone=masked,
        sub_reason=sub_reason,
        skipped=True,
    )
    if metrics_hook is not None:
        labels = {"class": klass.value}
        if sub_reason is not None:
            labels["sub_reason"] = sub_reason
        metrics_hook(SKIP_METRIC_NAME, 1.0, labels)
