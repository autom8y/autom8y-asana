"""Process-scoped warm deadline -- lets deep retry loops yield before the Lambda wall.

THE DEFECT THIS CURES (F1a pacing, root cause of the OfferFrameAgeSeconds sawtooth):
the cache-warmer's per-item loop checks ``_should_exit_early(context)`` only BETWEEN
items (``lambda_handlers/cache_warmer.py``). A single item whose warm rides a 429-retry
storm burns the entire remaining budget INSIDE the transport retry loop
(``transport/asana_http.py`` -- three ``while True`` loops that call ``_wait_for_retry``)
with NO deadline awareness, so the invocation is SIGKILLed at the 900 s wall mid-retry.
A hard timeout strands the sweep: the in-flight key is never checkpointed and NO
self-invoke continuation fires, so the offer frame goes stale for hours -> the sawtooth
peak -> the ASR readiness gate aborts.

LIVE FORENSICS (own-hands, acct 696318035277,
``/aws/lambda/autom8-asana-cache-warmer-bulk``, 7 d to 2026-08-05): 229 of 932
invocations (24.6 %) hard-timed-out at the wall; a sampled SIGKILL (req
557f3498..., 07:51:38Z) died 11.6 min after its last ``retry_waiting attempt=5
max_retries=5`` with no graceful yield. 125,778 rate-limit/retry log events in the
same window -- the storm is continuous.

THE CURE: publish a PROCESS-SCOPED monotonic deadline that the warmer handler arms
once from the Lambda context. The transport retry funnel (``_wait_for_retry``)
consults it and raises :class:`WarmDeadlineExceeded` instead of sleeping into the
wall; the warm orchestration catches that signal and checkpoints + self-invokes
gracefully -- the SAME continuation the per-item timeout branch already uses. A hard
SIGKILL strand becomes a graceful continue, so the sweep never stalls for hours.

INERT UNLESS ARMED: disarmed is the default and the state of every non-warmer process
(ECS serving, the API, workflow Lambdas never arm it), so ``_wait_for_retry`` is
byte-identical to origin/main for every path except an armed warmer that has actually
crossed its deadline. An env kill-switch (``ASANA_WARMER_DEADLINE_YIELD_ENABLED``,
default true) disarms the yield without a redeploy (fleet env-only-revert doctrine).

WHY :class:`BaseException`: the signal MUST NOT be swallowed by the broad
``except Exception`` / ``except CACHE_TRANSIENT_ERRORS`` handlers along the build path
(``warm_key_async``, ``hierarchy_warmer``, the per-entity isolation catch). Only the
explicit orchestration catch in ``cache_warmer.py`` handles it. This is the standard
control-flow-exception pattern (cf. ``asyncio.CancelledError``); context-manager
cleanup (``async with AsanaClient`` / semaphores) still runs on BaseException, so no
resource leaks.
"""

from __future__ import annotations

import os
import time
from typing import Any

from autom8y_log import get_logger

__all__ = [
    "DEADLINE_BUFFER_MS",
    "WarmDeadlineExceeded",
    "arm_warm_deadline",
    "disarm_warm_deadline",
    "raise_if_warm_deadline_reached",
    "warm_deadline_armed",
    "warm_deadline_reached",
]

logger = get_logger(__name__)

# Yield this many ms BEFORE the hard Lambda timeout. Mirrors
# ``lambda_handlers.timeout.TIMEOUT_BUFFER_MS`` (the per-item ``_should_exit_early``
# buffer) so the retry-loop yield and the per-item yield fire at the SAME instant --
# a drift-guard test asserts the two constants are equal.
DEADLINE_BUFFER_MS = 120_000

# Instant, no-redeploy revert lever (fleet env-only-revert doctrine). Default ENABLED;
# any of the falsey tokens below disarms the retry-loop yield so ``_wait_for_retry`` is
# byte-identical to origin/main again (the per-item ``_should_exit_early`` branch is
# unaffected -- this knob governs ONLY the deep retry-loop yield this module adds).
_ENABLE_ENV = "ASANA_WARMER_DEADLINE_YIELD_ENABLED"
_FALSEY = frozenset({"false", "0", "no", "off", ""})

# Process-scoped monotonic deadline (seconds on ``time.monotonic``'s clock). AWS Lambda
# runs exactly one invocation per execution environment at a time, so a module global is
# per-invocation-scoped by construction -- the same rationale the budget-allocator
# singleton uses. ``None`` == disarmed == INERT passthrough.
_deadline_monotonic: float | None = None


class WarmDeadlineExceeded(BaseException):
    """Control-flow signal: an armed warm deadline was reached inside a deep retry loop.

    Subclasses :class:`BaseException` (not :class:`Exception`) so the broad
    ``except Exception`` handlers on the warm build path do NOT swallow it; only the
    explicit orchestration catch converts it into a graceful checkpoint + self-invoke.
    """


def _yield_enabled() -> bool:
    raw = os.environ.get(_ENABLE_ENV)
    if raw is None:
        return True
    return raw.strip().lower() not in _FALSEY


def arm_warm_deadline(context: Any, *, buffer_ms: int = DEADLINE_BUFFER_MS) -> bool:
    """Arm the process-scoped warm deadline from a Lambda ``context``.

    The deadline is set ``(remaining_ms - buffer_ms)`` in the future on the monotonic
    clock, so :func:`warm_deadline_reached` becomes true exactly when the per-item
    ``_should_exit_early`` would (``remaining_ms < buffer_ms``). No-op (disarms) when the
    yield is env-disabled, ``context`` is ``None``, ``context`` lacks
    ``get_remaining_time_in_millis``, or the getter raises -- a broken/absent context must
    never make a warmer WORSE than origin/main.

    Returns:
        True if a deadline was armed, False if this call left the deadline disarmed.
    """
    global _deadline_monotonic
    if context is None or not _yield_enabled():
        _deadline_monotonic = None
        return False
    getter = getattr(context, "get_remaining_time_in_millis", None)
    if getter is None:
        _deadline_monotonic = None
        return False
    try:
        remaining_ms = int(getter())
    except Exception:  # noqa: BLE001 -- defensive: a broken context disarms, never harms
        _deadline_monotonic = None
        return False
    slack_seconds = max(0.0, (remaining_ms - buffer_ms) / 1000.0)
    _deadline_monotonic = time.monotonic() + slack_seconds
    logger.info(
        "warm_deadline_armed",
        extra={
            "remaining_ms": remaining_ms,
            "buffer_ms": buffer_ms,
            "slack_seconds": slack_seconds,
        },
    )
    return True


def disarm_warm_deadline() -> None:
    """Disarm the deadline (INERT passthrough). Idempotent; safe on any exit path."""
    global _deadline_monotonic
    _deadline_monotonic = None


def warm_deadline_armed() -> bool:
    """Whether a deadline is currently armed in this process."""
    return _deadline_monotonic is not None


def warm_deadline_reached() -> bool:
    """True iff a deadline is armed AND the monotonic clock has reached it.

    Disarmed (the default and every non-warmer process) always returns False, which is
    what makes the ``_wait_for_retry`` guard a byte-identical no-op off the warmer path.
    """
    deadline = _deadline_monotonic
    return deadline is not None and time.monotonic() >= deadline


def raise_if_warm_deadline_reached() -> None:
    """Raise :class:`WarmDeadlineExceeded` iff the armed deadline has been reached.

    Called by the transport retry funnel before each backoff sleep so a 429 storm yields
    control to the orchestration loop (graceful checkpoint + self-invoke) rather than
    sleeping into the 900 s SIGKILL.
    """
    if warm_deadline_reached():
        raise WarmDeadlineExceeded(
            "warm deadline reached inside a retry loop; yielding to checkpoint+continue"
        )
