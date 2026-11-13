"""D6 receiver signals: request outcomes, delivery results, undecided age (section 7).

Design of record: TDD-asana-bench-D6-shadow-receiver-20261110 r4.10, sections 4 and 7.

Each signal is emitted twice: as a Prometheus series on the default registry (the app
serves ``/metrics``), and as one structured log line, so an alarm can ride either a
metric or a log metric filter. The alarms themselves are not in this PR; section 7 names
the signals they read:

* 413s, 415s, signature mismatches, handshake refusals and ``compromised`` marks are
  ``autom8y_asana_hook_requests_total{outcome}`` and ``hook_request`` log lines;
* undecided age is ``autom8y_asana_hook_undecided_oldest_seconds``, set by the sweeper;
* abandoned deliveries are ``autom8y_asana_hook_deliveries_total{result="abandoned"}``.

Labels are closed sets. No label and no log field ever carries a handle, a gid, a header
value or a body (auth-bench A3-1; LEAK-1). Log lines about one hook carry ``handle_fp``,
a short one-way digest.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from autom8y_log import get_logger
from prometheus_client import Counter, Gauge

logger = get_logger(__name__)


class RequestOutcome(StrEnum):
    """Every way one request to the hook route ends. A closed label set."""

    SHADOW_OFF = "shadow_off"
    RECEIVER_UNAVAILABLE = "receiver_unavailable"
    UNKNOWN_HANDLE = "unknown_handle"
    ENCODING_REFUSED = "encoding_refused"
    TOO_LARGE = "too_large"
    SIGNATURE_INVALID = "signature_invalid"
    SIGNATURE_MISMATCH = "signature_mismatch"
    KEY_UNAVAILABLE = "key_unavailable"
    REGISTRY_UNAVAILABLE = "registry_unavailable"
    NOT_ACTIVE = "not_active"
    BODY_INVALID = "body_invalid"
    PERSIST_FAILED = "persist_failed"
    ACCEPTED = "accepted"
    HEARTBEAT = "heartbeat"
    HANDSHAKE_ECHOED = "handshake_echoed"
    HANDSHAKE_REFUSED = "handshake_refused"
    HANDSHAKE_COMPROMISED = "handshake_compromised"
    HANDSHAKE_STORE_FAILED = "handshake_store_failed"
    HANDSHAKE_THROTTLED = "handshake_throttled"


class DeliveryResult(StrEnum):
    """What happened to one persisted delivery after the 200. A closed label set."""

    PERSISTED = "persisted"
    REDELIVERED = "redelivered"
    CLAIM_LOST = "claim_lost"
    DECIDED = "decided"
    DEFERRED = "deferred"
    DECIDE_FAILED = "decide_failed"
    ABANDONED = "abandoned"


_ERROR_OUTCOMES: Final[frozenset[RequestOutcome]] = frozenset(
    {
        RequestOutcome.RECEIVER_UNAVAILABLE,
        RequestOutcome.KEY_UNAVAILABLE,
        RequestOutcome.REGISTRY_UNAVAILABLE,
        RequestOutcome.PERSIST_FAILED,
        RequestOutcome.HANDSHAKE_COMPROMISED,
        RequestOutcome.HANDSHAKE_STORE_FAILED,
    }
)
_INFO_OUTCOMES: Final[frozenset[RequestOutcome]] = frozenset(
    {RequestOutcome.ACCEPTED, RequestOutcome.HEARTBEAT, RequestOutcome.HANDSHAKE_ECHOED}
)
# Outcomes that attacker traffic can produce at volume and that are not section 7 alarm
# signals: counted always, logged at debug only, so a flood cannot flood the logs.
_QUIET_OUTCOMES: Final[frozenset[RequestOutcome]] = frozenset(
    {RequestOutcome.SHADOW_OFF, RequestOutcome.UNKNOWN_HANDLE}
)

HOOK_REQUESTS = Counter(
    "autom8y_asana_hook_requests_total",
    "D6 hook route requests by outcome (no handle, gid or header value in any label)",
    labelnames=["outcome"],
)
HOOK_DELIVERIES = Counter(
    "autom8y_asana_hook_deliveries_total",
    "D6 persisted deliveries by post-response result",
    labelnames=["result"],
)
HOOK_UNDECIDED_OLDEST_SECONDS = Gauge(
    "autom8y_asana_hook_undecided_oldest_seconds",
    "Age of the oldest undecided D6 delivery, set by the sweeper (0 when none)",
)


def record_request(outcome: RequestOutcome, *, handle_fp: str | None = None) -> None:
    """Count one request outcome and log it. ``handle_fp`` only, never the handle."""
    HOOK_REQUESTS.labels(outcome=outcome.value).inc()
    extra: dict[str, str] = {"outcome": outcome.value}
    if handle_fp is not None:
        extra["handle_fp"] = handle_fp
    if outcome in _QUIET_OUTCOMES:
        logger.debug("hook_request", extra=extra)
    elif outcome in _ERROR_OUTCOMES:
        logger.error("hook_request", extra=extra)
    elif outcome in _INFO_OUTCOMES:
        logger.info("hook_request", extra=extra)
    else:
        logger.warning("hook_request", extra=extra)


def record_delivery(result: DeliveryResult, *, handle_fp: str, attempts: int = 0) -> None:
    """Count one delivery result and log it."""
    HOOK_DELIVERIES.labels(result=result.value).inc()
    extra: dict[str, str | int] = {
        "result": result.value,
        "handle_fp": handle_fp,
        "attempts": attempts,
    }
    if result in (DeliveryResult.ABANDONED, DeliveryResult.DECIDE_FAILED):
        logger.error("hook_delivery", extra=extra)
    else:
        logger.info("hook_delivery", extra=extra)


def record_undecided_age(oldest_seconds: int) -> None:
    """Set the undecided-age gauge (section 7 "undecided age")."""
    HOOK_UNDECIDED_OLDEST_SECONDS.set(max(0, int(oldest_seconds)))
    logger.info("hook_undecided_age", extra={"undecided_oldest_seconds": int(oldest_seconds)})
