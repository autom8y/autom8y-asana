"""Run-scoped budget governor for the operator-plane batch path (TDD §5.1).

The cross-tenant agency-BI export issues operator-route calls under a per-identity
``LIMIT_HEAVY_ANALYTICS = "10/minute"`` DoS guard on the data plane (INV-1, never
weakened by this cure). :class:`OperatorCallPacer` self-limits the export STRICTLY
below that guard so the guard stays armed for everything else while the export never
trips it:

- A hard **run budget** (``B_run``, default 9 < 10) caps the AGGREGATE wire calls
  per export run across ALL operator insights AND the bisection recursion -- ONE
  shared counter, not one-per-insight (TDD ADR-003 / RISK-5). When the budget is
  spent, :meth:`acquire` raises :class:`BudgetExhausted`; the caller serves what it
  reached and flags the run partial (graceful, prior decks intact -- RISK-4).
- A token-bucket **window limit** (default 10 / 60s, mirroring the server window)
  paces calls so no rolling 60s window exceeds the limit. With ``B_run = 9`` the
  run can never reach 10 calls total, so the window limiter is dormant by default;
  it becomes load-bearing only if ``run_budget`` is raised above the window for a
  larger fleet (the ceiling is config -- ADR-003, two-way reversible).

On a server 429 the pacer honors ``Retry-After`` (clamped) before the caller
retries, reusing the ADR-0079 retry-classification primitive
(:class:`~autom8_asana.patterns.error_classification.RetryableErrorMixin` via
:meth:`RateLimitError.from_response`, conventions.md:65).

The pacer is constructed once per run (fresh per ``_prefetch_operator_tables``) and
is stateless across runs. It also accumulates the set of offices it could NOT serve
this run because the budget/throttle stopped it (``unreached``); the workflow uses
that set to PROTECT those offices' prior decks (no destructive empty-deck overwrite
-- the per-office mirror of the whole-plane INERT no-op guard, RISK-4).

This module is NOT part of the public API.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import TYPE_CHECKING, Any

from autom8_asana.patterns.error_classification import RetryableErrorMixin

if TYPE_CHECKING:  # pragma: no cover -- typing only
    from collections.abc import Callable, Coroutine, Iterable

    from autom8_asana.errors import AsanaError

# Conservative per-run ceiling: strictly BELOW the server's 10/min guard so the
# export self-limits and the guard stays armed (and fires at the 11th) for anything
# that would. The <10 margin also absorbs client/server window clock skew (RISK-6).
DEFAULT_RUN_BUDGET = 9

# Server rate window (mirrors LIMIT_HEAVY_ANALYTICS = "10/minute"). Dormant while
# DEFAULT_RUN_BUDGET (9) < DEFAULT_WINDOW_LIMIT (10); load-bearing if the run budget
# is later raised above the window for a larger fleet.
DEFAULT_WINDOW_SECONDS = 60.0
DEFAULT_WINDOW_LIMIT = 10

# Bound the honored Retry-After sleep so a hostile/garbage header cannot wedge a run.
DEFAULT_MAX_RETRY_AFTER_SECONDS = 30.0

# Fallback backoff when a 429 carries no parseable Retry-After header.
DEFAULT_RETRY_AFTER_FALLBACK_SECONDS = 1.0


class BudgetExhausted(Exception):
    """The per-run operator-call budget (``B_run``) is spent; stop issuing calls.

    Raised by :meth:`OperatorCallPacer.acquire`. The caller serves whatever it
    reached so far (partial), marks the unreached offices for prior-deck
    protection, and returns gracefully -- it is NEVER a crash and NEVER a trigger
    for the SA fleet-read fallback (G-NO-FALLBACK).
    """


class _ResponseRetrySignal(RetryableErrorMixin):
    """Adapter: classify a throttle ``Response`` via the ADR-0079 mixin.

    Wraps a 429/5xx response as the typed :class:`AsanaError` the
    :class:`RetryableErrorMixin` was built to classify, so the pacer reuses the
    canonical ``retry_after_seconds`` (ADR-0079) Retry-After extraction rather than
    re-implementing header parsing. ``RateLimitError.from_response`` parses the
    ``Retry-After`` header; the mixin property then reads it off the error.
    """

    def __init__(self, response: Any) -> None:
        self._response = response

    def _get_error(self) -> AsanaError | None:
        from autom8_asana.errors import AsanaError, RateLimitError

        status = getattr(self._response, "status_code", None)
        if status == 429:
            return RateLimitError.from_response(self._response)
        return AsanaError.from_response(self._response)


def retry_after_seconds(response: Any) -> int | None:
    """Extract a Retry-After delay (seconds) from a throttle response.

    Reuses the ADR-0079 :class:`RetryableErrorMixin.retry_after_seconds` property
    (conventions.md:65). Returns ``None`` when the response carries no parseable
    ``Retry-After`` header. Never raises -- a malformed response must not crash
    pacing.
    """
    try:
        return _ResponseRetrySignal(response).retry_after_seconds
    except Exception:  # noqa: BLE001 -- pacing must survive any malformed response
        # Defensive fallback: read the header directly.
        headers = getattr(response, "headers", None)
        if not headers:
            return None
        raw = headers.get("retry-after") or headers.get("Retry-After")
        try:
            return int(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None


class OperatorCallPacer:
    """Run-scoped token-bucket + hard-cap governor for operator-route wire calls.

    One instance is threaded across ALL operator insight calls and the bisection
    recursion within a single export run, so the aggregate wire count is bounded by
    a SINGLE shared counter (``B_run``) -- holding INV-1 (the 10/min DoS guard) by
    self-limiting strictly below it.
    """

    def __init__(
        self,
        *,
        run_budget: int = DEFAULT_RUN_BUDGET,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        window_limit: int = DEFAULT_WINDOW_LIMIT,
        max_retry_after_seconds: float = DEFAULT_MAX_RETRY_AFTER_SECONDS,
        sleep: Callable[[float], Coroutine[Any, Any, None]] = asyncio.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if run_budget < 1:
            raise ValueError(f"run_budget must be at least 1, got {run_budget}")
        self._run_budget = run_budget
        self._window_seconds = window_seconds
        self._window_limit = window_limit
        self._max_retry_after_seconds = max_retry_after_seconds
        self._sleep = sleep
        self._monotonic = monotonic

        self._spent = 0
        self._calls: deque[float] = deque()
        self._partial = False
        self.unreached: set[str] = set()

    @property
    def run_budget(self) -> int:
        """The hard aggregate wire-call ceiling for this run."""
        return self._run_budget

    @property
    def spent(self) -> int:
        """Aggregate wire calls acquired this run (the shared counter)."""
        return self._spent

    @property
    def partial(self) -> bool:
        """True if the run could not complete within budget / under throttle."""
        return self._partial

    async def acquire(self) -> None:
        """Reserve one wire call; pace to the window; enforce the run budget.

        Raises:
            BudgetExhausted: the per-run hard cap is reached -- the caller must stop
                issuing calls, serve what it reached, and flag the run partial.
        """
        if self._spent >= self._run_budget:
            self._partial = True
            raise BudgetExhausted(
                f"operator run budget ({self._run_budget}) exhausted after "
                f"{self._spent} wire call(s)"
            )

        # Token-bucket window pacing: evict calls older than the window; if the
        # window is full, wait until the oldest call ages out, then re-evict.
        now = self._monotonic()
        self._evict(now)
        if len(self._calls) >= self._window_limit:
            wait = self._calls[0] + self._window_seconds - now
            if wait > 0:
                await self._sleep(wait)
            now = self._monotonic()
            self._evict(now)

        self._calls.append(now)
        self._spent += 1

    def _evict(self, now: float) -> None:
        cutoff = now - self._window_seconds
        while self._calls and self._calls[0] <= cutoff:
            self._calls.popleft()

    async def honor_retry_after(self, response: Any) -> None:
        """Sleep the response's advertised ``Retry-After`` (clamped) before a retry.

        Falls back to a small backoff when no parseable header is present. The
        sleep is clamped to ``max_retry_after_seconds`` so a garbage header cannot
        wedge the run.
        """
        advertised = retry_after_seconds(response)
        delay = (
            float(advertised) if advertised is not None else DEFAULT_RETRY_AFTER_FALLBACK_SECONDS
        )
        delay = min(max(delay, 0.0), self._max_retry_after_seconds)
        if delay > 0:
            await self._sleep(delay)

    def mark_unreached(self, phones: Iterable[str]) -> None:
        """Record offices NOT served this run (budget/throttle/transient skip).

        Flags the run partial and adds the offices to :attr:`unreached`. The
        workflow protects those offices' prior decks (no destructive empty-deck
        overwrite -- RISK-4). Definitively-answered offices (served, drift-404, or
        plane-closed) are NEVER marked unreached.
        """
        self._partial = True
        self.unreached.update(phones)
