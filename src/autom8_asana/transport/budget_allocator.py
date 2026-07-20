"""F1a cross-consumer rate-limit budget allocator -- process-singleton, advisory.

Per HANDOFF-arch-to-10x-f1a-budget-allocator-2026-07-20 (node 5 BUILD) and the
pythia ADVISORY published-floor ruling (ADJUDICATION-option-slate.md). The fleet
shares ONE Asana ``1500/60s`` budget across 11 principals (ECS + 10 workflow
Lambdas) with per-process-only AIMD and NO cross-consumer arbitration. Today's
failure is MALDISTRIBUTION: ECS monopolizes in bursts (100% of measured 429s);
the substrate warmer self-suppresses toward 0 because its own AIMD reads the
GLOBAL 429 signal.

This module is the allocator core: a UNIFIED in-process singleton that publishes
a STATIC, C-11-decoupled floor and telemeters overage ADVISORILY (never a hard
block). Every failure direction is FAIL-OPEN (a lane proceeds un-arbitrated),
never fail-closed (which would make the storm worse -- the exact shift-starvation
the node-4 adversary gate defeated).

INERT AT MERGE (F-a): the allocator ships with ``ASANA_BUDGET_ALLOCATOR_ENABLED``
default FALSE. Disabled => byte-identical no-op passthrough at the seam (ITEM-D).
Activation is OPERATOR-ONLY at the GO-LIVE gate; node 5 never sets it true
outside scoped test fixtures.

=============================================================================
PYTHIA HARD CONDITIONS (PC-1..PC-5) -- transcribed VERBATIM from
``.sos/wip/thermia/f1a/ADJUDICATION-option-slate.md`` §4 (do NOT paraphrase):
=============================================================================

  1. Unified in-process singleton limiter (C-2 + C-3). ECS's 1390 self-cap MUST
     be enforced by ONE process-level-singleton limiter at the client-
     construction seam (``client.py.__init__`` / transport), unifying all
     ~55-57 ``AsanaClient(`` sites so no ephemeral bypass escapes the cap; the
     same singleton carries C-3 intra-process priority (``/section-timelines``
     P1 > self-generated warm F). BUILD-GATE (ITEM-D, 3d §2.2): ``ENABLED=false``
     => call pattern byte-identical to the 57-site baseline; the knob's settings
     bind MUST be per-process-fresh, not import-time-once -- else HALT node 5.

  2. Published static C-11-decoupled floor via CONFIG, not Redis (C-11). Publish
     the 110/60s warmer floor as a near-static config/env value reachable by all
     11 principals (incl. the 4 Redis-unreachable Lambdas) and surviving publish-
     surface death as data-at-rest; the warmer proceeds within 110 decoupled from
     the global 429; AIMD stays underneath.

  3. Per-lane fail-open = 3d Axis-B verbatim (C-4). DEGRADED and KILLED resolve
     to the identical per-lane code path: warmer->static floor (plain-AIMD
     FORBIDDEN), ECS->AIMD or retained static 1390, InMemory-4->static/immaterial.
     One knob, no per-lane sub-knobs.

  4. Bounded-overshoot cap sizing (C-6). Hard-reserve only the 110; ECS self-caps
     1390; near-zero principals self-cap at measured-draw+modest-headroom with
     Sigma(all self-caps) <= ~1550 (~3-4% worst-case, 429-backstopped, warmer-
     insulated). Do NOT hard-subdivide the 1390; do NOT generously cap the near-
     zero set. The <=7.3% unclaimed-floor-when-idle dead capacity is accepted.

  5. Deployment-ordering (R6) gated by INERT-default + convergence. Cond-1's
     unification activates only on full 11-process redeploy -> mixed-fleet mid-
     rollout; mitigated because default = INERT (knob false) and activation is
     operator-only (F-a) AFTER the activation-convergence gauge (3d transition
     #2, N-of-11) confirms full rollout. Operator confirms convergence at GO-LIVE.

=============================================================================
ADVERSARY CONDITIONS (AC-1..AC-6) -- transcribed VERBATIM from
``.sos/wip/thermia/f1a/ADVERSARY-REPORT-f1a-1.md`` §6 (do NOT paraphrase):
=============================================================================

  1. Unification-totality census (hardens HARD-cond-1). Static build-gate
     asserting: (a) every ``AsanaClient(`` site resolves to the process
     singleton; (b) ZERO sites pass an explicit rate-limiter/config injection
     that bypasses it (ADR-0062 injection audit -- reconcile with killswitch-spec
     §2.4-item-3's preserved override precedence: overrides may exist for TESTS
     only, never in ``src/``); (c) ZERO non-AsanaClient egress to
     ``app.asana.com``. Discharge: CI census script in the node-5 PR; RED arm =
     inject one bypass site, census must fail.

  2. Runtime cap-leak reconciliation observable. Per-minute singleton-admitted-
     count vs httpx-observed outbound-count (the request line already exists in
     ECS logs); delta > epsilon -> alarm. Converts CH-01's silent leak into a
     detected leak; this is the ONLY aggregate ground truth advisory has.
     Discharge: node-5 build AC (metric emission) + node-9 threshold.

  3. C-11 instrumentation PRECONDITION with a falsifiable prediction. Before the
     GREEN arm counts: instrument semaphore window size, admission waits, and
     chunk progress per invocation; the RED-arm fixture must REPRODUCE the
     production suppression signature under plain-AIMD wiring. Prediction (binds
     the build): with floor-admission at 110/min, a 3,291-GET sweep completes
     within <=1800s of warm-window wall-clock. Falsified -> mechanism is not
     admission-limited -> floor re-derivation before merge. Discharge:
     DEFER-BUILD-C11 hardened into a node-5 AC with the stated prediction; canary
     must prove cap+floor JOINTLY (the pay-cost-no-cure conjunction of §2a is the
     failure to catch).

  4. TASK-entry TTL resolved BEFORE floor-value finalization. Static read of the
     ``EntryType.TASK`` TTL; if < 1800s, re-derive §1.4's time budget (the
     regrowth loop otherwise survives the floor). Promotes capacity-spec
     §8-item-5 from recommended to required. Discharge: file:line receipt in
     HANDOFF-2 naming the constant.

  5. Near-zero caps sized from measurement, not window-artifact zeros. Node-5
     census must include (a) a CWLI window containing a Sunday 07:00Z
     ``conversation-audit`` firing, (b) the 11:00Z burst of ``insights-export`` +
     ``onboarding-walkthrough`` (scheduled same-minute collision inside the
     diurnal peak), before fixing their static caps. Discharge: measured per-
     principal burst table appended to the census.

  6. Warmer-lane 429 alarm coherence. Reconcile capacity-spec §1.3's zero-429-on-
     floor expectation with T4's accepted <=3-4% overshoot and the deploy-
     transient window: set the mis-enforcement alarm threshold ABOVE the expected
     overshoot-driven warmer-429 noise floor (~3-5/min worst case), and correct
     the "does not touch the warmer" wording in HANDOFF-2. Discharge: node-9
     observability threshold spec + HANDOFF-2 wording fix.

=============================================================================
BUILD DISPOSITION of the conditions above (node-5 scope):
  PC-1  BUILT   -- process singleton + client-seam attach (ITEM-B) + byte-
                   identical/per-process-fresh (ITEM-D).
  PC-2  BUILT   -- ``published_floor()`` is a pure config read; NO AIMD import.
  PC-3  BUILT   -- ``fail_open`` per-lane wrapper + ``budget_lane_failopen``.
  PC-4  BUILT   -- floor 110 + fair_share 1390 partition constants (config).
  PC-5  BUILT   -- INERT default; convergence gauge = node-9/operator (F-a).
  AC-1  BUILT   -- census grep-assertion test (ITEM-B).
  AC-2  BUILT   -- ``budget_floor_overage`` admitted-vs-cap observable (metric);
                   node-9 owns the alarm threshold.
  AC-3  BUILT   -- warmer floor-admission sweep gate <=1800s @ 110/60s (ITEM-C).
  AC-4  RESOLVED -- ``EntryType.TASK`` TTL = entity-typed via TaskTTLResolver
                   (clients/task_ttl.py:60-99): business=3600 / unit=900 /
                   offer=180 / process=60 / generic=DEFAULT_TTL=300 (config.py
                   :132). Generic gap-parent TTL 300s < 1800s => the static floor
                   cures the ADMISSION starvation it is sized for but does NOT
                   structurally break the TTL-regrowth loop for 300s parents.
                   Floor value NOT fudged; regrowth re-derivation routed to arch.
  AC-5  DEFER   -- near-zero caps from live CWLI measurement forbidden by F-b
                   (zero live probes at node 5); soft-caps remain config default
                   with the measured-draw note -> honest gap, node-9/operator.
  AC-6  DEFER   -- warmer-lane 429 alarm threshold = node-9 observability spec.
=============================================================================
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.config import BudgetAllocatorConfig

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from autom8y_log import LoggerProtocol

__all__ = [
    "BudgetAllocator",
    "Lane",
    "PublishedFloor",
    "WarmerFloorGate",
    "get_budget_allocator",
    "reset_budget_allocator",
    "set_budget_allocator",
]

logger = get_logger(__name__)

# Token-bucket admission tolerance -- see WarmerFloorGate.admit for the ULP trap.
_ADMIT_EPSILON = 1e-9


class Lane(StrEnum):
    """Consumer lane classification (C-3 priority tiers, capacity-spec §3).

    WARMER      -- P0 protected substrate warmer; claims the static floor.
    FAIR_SHARE  -- F fair-share pool (ECS + near-zero batch Lambdas); AIMD-governed.
    CLIENT_FELT -- C client-felt / client-felt-ADJACENT (/section-timelines,
                   insights-export); ranked above the warmer floor by policy.
    """

    WARMER = "warmer"
    FAIR_SHARE = "fair_share"
    CLIENT_FELT = "client_felt"


@dataclass(frozen=True)
class PublishedFloor:
    """The static, C-11-decoupled floor the allocator publishes (data-at-rest).

    This is a pure value object. Reading it invokes NO AIMD / dynamic concurrency
    instrumentation (pythia PC-2 / C-11): the floor survives publish-surface death
    by construction, which is what makes the advisory seam fail-open-to-static-
    floor natively.
    """

    max_requests: int
    window_seconds: int

    @property
    def rate_per_second(self) -> float:
        """Sustained floor rate (calls/second)."""
        return self.max_requests / self.window_seconds


class WarmerFloorGate:
    """Rate-based admission gate for the warmer lane's static floor (ITEM-C).

    Admits up to ``floor.max_requests`` calls per ``floor.window_seconds`` at a
    sustained rate, refilling continuously (leaky/token bucket). Two load-bearing
    properties for the F1a cure:

    * QUEUE-POSITION-INDEPENDENT (capacity-spec §1.1): any caller with floor
      budget is admitted regardless of its position in the warmer's 68-key list.
      The offer key at list positions 17-18/68 -- one key PAST the 16-key bulk
      budget (``_DEFAULT_BULK_KEY_BUDGET``, cache_warmer.py) -- is served, not
      starved behind the 8 heavier GIDs ahead of it.

    * AIMD-DECOUPLED (C-11): this gate never reads the AIMD window or the global
      429 signal. Under AIMD self-suppression (window collapses toward floor=1),
      the warmer STILL admits at the static floor rate through this gate -- the
      static floor OVERRIDES AIMD self-suppression (does not oscillate to ~0 as
      observed 2026-07-14). AIMD remains underneath as the belt-and-suspenders
      overflow path for calls BEYOND the floor grant.

    The clock and sleep are injectable so the sweep-gate build test (AC-3) runs
    in-silico with a mocked clock -- ZERO real sleeps, ZERO live Asana calls (F-b).

    The bucket starts EMPTY: admission is a sustained RATE guarantee (the AC-3
    sweep is a sustained-demand scenario), so tokens are earned at the floor rate
    rather than pre-filled. This models capacity-spec §1.5's derivation exactly
    (3,291 / (110/60) ~= 1795s) rather than optimistically.
    """

    def __init__(
        self,
        floor: PublishedFloor,
        *,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._floor = floor
        self._rate = floor.rate_per_second
        self._capacity = float(floor.max_requests)
        self._tokens = 0.0  # start EMPTY -- earn every token at the floor rate
        self._clock: Callable[[], float] = clock or _default_monotonic
        self._sleep: Callable[[float], Awaitable[None]] = sleep or asyncio.sleep
        self._last = self._clock()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last
        if elapsed > 0:
            self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
            self._last = now

    async def admit(self) -> None:
        """Admit exactly one floor-protected call.

        Returns immediately when floor budget remains; otherwise waits ONLY long
        enough to earn the next token at the floor rate. Never consults AIMD.

        The ``_ADMIT_EPSILON`` tolerance guards the classic token-bucket
        floating-point trap: ``wait * rate`` can compute to ``0.99999999999`` (one
        ULP below 1.0), which would otherwise spin forever on a sub-epsilon
        deficit as the clock advancement underflows.
        """
        async with self._lock:
            while True:
                self._refill()
                if self._tokens >= 1.0 - _ADMIT_EPSILON:
                    self._tokens = max(0.0, self._tokens - 1.0)
                    return
                deficit = 1.0 - self._tokens
                wait = deficit / self._rate if self._rate > 0 else 0.0
                await self._sleep(wait)


class BudgetAllocator:
    """Unified in-process singleton advisory limiter (pythia PC-1, the flagship).

    ONE instance per process reconciles the existing per-``AsanaClient`` AIMD
    (``transport/adaptive_semaphore.py``) with the new static budget floor. It is
    ADVISORY: it publishes a floor and telemeters overage; it never hard-blocks a
    request (an advisory limiter is never in the request path, so its failure
    fails OPEN to today's un-arbitrated behavior, not to total starvation -- this
    is what defeats the SPOF/single-writer liability, architecture-assessment.md
    §5).

    When ``enabled`` is False the allocator is a byte-identical no-op passthrough
    at the seam (ITEM-D): callers early-return before any interposition.
    """

    def __init__(
        self,
        config: BudgetAllocatorConfig,
        *,
        log_provider: LoggerProtocol | None = None,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._config = config
        self._log: LoggerProtocol = log_provider or logger
        self._clock: Callable[[], float] = clock or _default_monotonic
        self._sleep: Callable[[float], Awaitable[None]] = sleep or asyncio.sleep

        # Advisory per-lane sliding-window admission counters (AC-2 cap-leak
        # reconciliation observable). Fair-share overage is TELEMETERED, never
        # blocked. Keyed by lane; each value is (window_start, admitted_count).
        self._counters: dict[Lane, tuple[float, int]] = {}
        self._counter_lock = threading.Lock()

        # Registered clients (PC-1 unification bookkeeping). Advisory only: the
        # singleton is aware of every AsanaClient constructed while ACTIVE so the
        # per-minute admitted-count ground truth (AC-2) has a denominator. Never
        # mutates a client's request path.
        self._registered_client_ids: set[int] = set()

        # Startup INFO log (per-principal, at fresh construction) -- ITEM-D §2.3.
        state = "ACTIVE" if config.enabled else "INERT"
        self._log.info(
            "allocator_boot",
            extra={
                "state": state.lower(),
                "enabled": config.enabled,
                "floor_max_requests": config.floor_max_requests,
                "floor_window_seconds": config.floor_window_seconds,
                "fair_share_max_requests": config.fair_share_max_requests,
            },
        )

    # -- policy surface ------------------------------------------------------

    @property
    def enabled(self) -> bool:
        """Whether the allocator is ARMED. Default False => INERT passthrough."""
        return self._config.enabled

    @property
    def config(self) -> BudgetAllocatorConfig:
        """The bound configuration (data-at-rest)."""
        return self._config

    def published_floor(self) -> PublishedFloor:
        """Return the static warmer floor (C-11-DECOUPLED, pythia PC-2).

        This is a PURE config read. It invokes NO AIMD / dynamic concurrency
        instrumentation -- the floor value is data-at-rest and is readable whether
        the allocator is ACTIVE, INERT, or KILLED. The BUILD-GATE (ITEM-A TL-A)
        asserts this method reaches the 110/60s value with ZERO calls into
        adaptive_semaphore.
        """
        return PublishedFloor(
            max_requests=self._config.floor_max_requests,
            window_seconds=self._config.floor_window_seconds,
        )

    def warmer_floor_gate(
        self,
        *,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> WarmerFloorGate:
        """Construct a warmer floor-admission gate for the published floor (ITEM-C).

        The gate admits at the static floor rate, queue-position-independent and
        AIMD-decoupled. ``clock``/``sleep`` are injectable for the in-silico sweep
        gate (AC-3); they default to the allocator's own clock/sleep.
        """
        return WarmerFloorGate(
            self.published_floor(),
            clock=clock or self._clock,
            sleep=sleep or self._sleep,
        )

    # -- unification bookkeeping (PC-1) --------------------------------------

    def register_client(self, client_id: int) -> None:
        """Record an AsanaClient under the process singleton (PC-1 unification).

        Advisory bookkeeping only -- provides the denominator for the AC-2
        admitted-count ground truth. Never touches the client's request path.
        Idempotent. No-op semantics are preserved when the allocator is INERT
        (the caller early-returns before reaching here).
        """
        self._registered_client_ids.add(client_id)

    @property
    def registered_client_count(self) -> int:
        """Number of clients registered under the singleton (PC-1 denominator)."""
        return len(self._registered_client_ids)

    # -- advisory admission observation (AC-2 / ITEM-A AC3) ------------------

    def observe_admission(self, lane: Lane, *, count: int = 1) -> None:
        """ADVISORY: record ``count`` admissions on ``lane`` and telemeter overage.

        This NEVER blocks (advisory published-floor, not in-path arbiter). For a
        fair-share lane, when the sliding-window admitted count exceeds the
        fair-share cap (1390/60s) the overage is emitted as ``budget_floor_overage``
        -- the ONLY aggregate ground truth advisory has (AC-2). A hot recurring
        overage is the ``budget_floor_overage`` tripwire (DEFER-WATCH-CAP-LEAK):
        an ephemeral consumer leaking past the budget is BOUNDED-and-LOUD here,
        not silent-and-unbounded (canary pair (a)).
        """
        if not self._config.enabled:
            return
        # Warmer admissions are floor-protected, not fair-share; only the
        # fair-share pool is cap-telemetered (the warmer's 110 is a reservation,
        # not an overage source -- PC-4 warmer-insulation).
        if lane is Lane.WARMER:
            return

        cap = self._config.fair_share_max_requests
        window = self._config.floor_window_seconds
        now = self._clock()
        with self._counter_lock:
            window_start, admitted = self._counters.get(lane, (now, 0))
            if now - window_start >= window:
                window_start, admitted = now, 0
            admitted += count
            self._counters[lane] = (window_start, admitted)

        if admitted > cap:
            overage = admitted - cap
            self._log.warning(
                "budget_floor_overage",
                extra={
                    "lane": lane.value,
                    "admitted": admitted,
                    "cap": cap,
                    "overage": overage,
                    "window_seconds": window,
                },
            )

    # -- per-lane fail-open (pythia PC-3 / ITEM-B) ---------------------------

    def note_lane_failopen(self, lane: Lane, error: BaseException) -> None:
        """Emit the ``budget_lane_failopen`` tripwire.

        Fired when a limiter-internal exception is caught on ``lane`` and the lane
        is allowed to PROCEED un-arbitrated (fail-OPEN, never fail-closed -- a
        fail-closed limiter would make the storm worse, the exact shift-starvation
        the node-4 gate defeated). Other lanes are unaffected.
        """
        self._log.warning(
            "budget_lane_failopen",
            extra={
                "lane": lane.value,
                "error": str(error),
                "error_type": type(error).__name__,
            },
        )


# ---------------------------------------------------------------------------
# Process singleton (PC-1) -- lazy, per-process-fresh, resettable for tests.
# ---------------------------------------------------------------------------

_ALLOCATOR: BudgetAllocator | None = None
_ALLOCATOR_LOCK = threading.Lock()


def _default_monotonic() -> float:
    import time

    return time.monotonic()


def get_budget_allocator() -> BudgetAllocator:
    """Return the process-singleton allocator (pythia PC-1).

    Lazily constructed on FIRST access (never at import time) so the knob binds
    PER-PROCESS-FRESH via ``BudgetAllocatorConfig.from_env()`` -- the exact ITEM-D
    BUILD-GATE (killswitch-rollback-spec §2.2): an import-time-once bind would make
    flipping the env var a no-op until process restart, the dead-knob HALT
    condition. Identity is stable across all lanes: two callers observe the SAME
    instance (``id(a) == id(b)``).
    """
    global _ALLOCATOR
    if _ALLOCATOR is not None:
        return _ALLOCATOR
    with _ALLOCATOR_LOCK:
        if _ALLOCATOR is None:
            _ALLOCATOR = BudgetAllocator(BudgetAllocatorConfig.from_env())
    return _ALLOCATOR


def reset_budget_allocator() -> None:
    """Test-only: clear the process singleton so the next access re-reads env.

    Registered with ``SystemContext.reset_all()`` for cross-test isolation (the
    conftest leakage guard, ITEM-D §2.4-item-4).
    """
    global _ALLOCATOR
    with _ALLOCATOR_LOCK:
        _ALLOCATOR = None


def set_budget_allocator(allocator: BudgetAllocator | None) -> None:
    """Test-only: inject an explicit allocator (canary fixtures arm in-process).

    Mirrors ITEM-D §2.4-item-3's explicit-override precedence: the canary suite
    constructs the allocator directly with an armed config + fixture clock, never
    flipping a production env knob (F-a honored).
    """
    global _ALLOCATOR
    with _ALLOCATOR_LOCK:
        _ALLOCATOR = allocator


# Self-register for SystemContext.reset_all() (test isolation).
from autom8_asana.core.system_context import register_reset  # noqa: E402

register_reset(reset_budget_allocator)
