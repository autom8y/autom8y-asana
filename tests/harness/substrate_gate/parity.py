"""Parity runner scaffold (S7 · P5) — v2-beside-v1, per-divergence ledger.

REQUIREMENT 2 of the S7 build. For a (project, entity) the runner obtains a v1 and a
v2 materialization from a ``ParitySource`` and, on each mismatch, emits a
``DivergenceLedgerEntry`` carrying the FROZEN RC-A-2 ``RefusePayload`` observable AS
LANDED — all four fields (plane · absolute_age · magnitude · per_section_delta),
Mappings preserved, **not narrowed**. Every divergence is explained before any flip
(charter P5); the ledger entry IS that explanation.

DARK (WAVE-2): the live path is behind ``ParitySource``. The fixture source drives
wave-2 tests deterministically; the ``PacedLiveParitySource`` COMPOSES v1's existing
pacing controllers DIRECTLY — ``AsyncAdaptiveSemaphore`` (AIMD) + the
``BudgetAllocator`` warmer floor gate + ``core.retry`` orchestrator +
``gather_with_semaphore`` bounded fan-out — the way v1 does, and NEVER a direct
un-paced ``AsanaClient`` (RC-E-4 routing invariant). Its outbound leg raises
``LiveParityNotArmedError`` until S8 arms it: accidental live execution before S8 is
impossible, not merely discouraged.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from autom8_asana.config import BudgetAllocatorConfig
from autom8_asana.core.concurrency import gather_with_semaphore
from autom8_asana.core.retry import (
    BudgetConfig,
    CircuitBreaker,
    CircuitBreakerConfig,
    DefaultRetryPolicy,
    RetryBudget,
    RetryOrchestrator,
    RetryPolicyConfig,
    Subsystem,
)
from autom8_asana.errors import RateLimitError
from autom8_asana.transport.adaptive_semaphore import AIMDConfig, AsyncAdaptiveSemaphore
from autom8_asana.transport.budget_allocator import BudgetAllocator
from tests.harness.substrate_gate.divergence import (
    divergence_payload,
    diverges,
    explain_divergence,
    order_by_age,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable
    from datetime import datetime

    from autom8_asana.substrate.identity import ArtifactId
    from autom8_asana.substrate.serve import RefusePayload
    from tests.harness.substrate_gate.budget import PerDayBudgetLedger
    from tests.harness.substrate_gate.cases import Materialization


def _is_rate_limit_signal(exc: BaseException) -> bool:
    """True for a 429 signal the AIMD window must react to.

    Mirrors v1's ``isinstance(error, RateLimitError)`` test on the outbound leg
    (``transport.asana_http`` :485/:633/:723) AND covers rate-limit-EQUIVALENT
    errors that carry an HTTP 429 status without being the ``RateLimitError`` type
    (e.g. a raw ``AsanaError`` mapped from a 429 response). Non-429 failures return
    False — they must NOT shrink the concurrency window.
    """
    return isinstance(exc, RateLimitError) or getattr(exc, "status_code", None) == 429


@dataclass(frozen=True, slots=True)
class ParityObservation:
    """v2 beside v1 for one (project, entity): the two copies to be compared."""

    aid: ArtifactId
    v1: Materialization
    v2: Materialization


@dataclass(frozen=True, slots=True)
class DivergenceLedgerEntry:
    """One explained divergence — the RC-A-2 refusal payload plus its rendering.

    ``payload`` is the FROZEN ``substrate.serve.RefusePayload`` AS LANDED: the four
    fields are neither narrowed nor collapsed. ``explanation`` is the human-readable
    projection ('composition shift, not noise: ...').
    """

    artifact_key: str
    stale_plane: str
    fresh_plane: str
    payload: RefusePayload
    explanation: str


class ParitySource(Protocol):
    """Where the parity runner gets v1 + v2 for a (project, entity).

    Fixture-backed in wave-2; the live implementation is DARK until S8.
    """

    def fetch(self, aid: ArtifactId) -> ParityObservation:
        """Return the (v1, v2) observation for ``aid`` (or raise if a DARK path is unarmed)."""
        ...


class FixtureParitySource:
    """Deterministic, side-effect-free parity source for wave-2 replay."""

    def __init__(self, observations: Iterable[ParityObservation]) -> None:
        self._by_key: dict[str, ParityObservation] = {
            display_key(observation.aid): observation for observation in observations
        }

    def fetch(self, aid: ArtifactId) -> ParityObservation:
        return self._by_key[display_key(aid)]


class LiveParityNotArmedError(RuntimeError):
    """Raised when the DARK live-parity path is invoked before S8 arms it.

    The loud guard that makes accidental live prod execution impossible in wave-2.
    """


class ParityOutboundError(RuntimeError):
    """A parity outbound leg failed — the ``core.retry``-safe carrier for an Asana error.

    The resilience leg is ``core.retry.RetryOrchestrator``, whose transient-classifier
    (``retry._is_transient``) inspects a botocore-shaped ``.response`` dict. The Asana
    error hierarchy is INCOMPATIBLE with it: ``AsanaError.response`` is an httpx
    ``Response`` or ``None``, never a botocore dict, so feeding a raw Asana error to the
    orchestrator ``AttributeError``s inside the classifier and MASKS the real failure.
    This wrapper is a plain ``RuntimeError`` (no ``.response`` attribute → classifier-safe)
    carrying the original as ``__cause__``; ``status_code`` / ``rate_limited`` expose what
    the AIMD reject decision keyed off. The ``slot.reject()`` already fired BEFORE this
    is raised — the wrapper only bridges propagation, it does not gate the signal.
    """

    def __init__(
        self, message: str, *, status_code: int | None = None, rate_limited: bool = False
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.rate_limited = rate_limited


def _build_retry_orchestrator() -> RetryOrchestrator:
    """Compose the ``core.retry`` orchestrator (policy + budget + circuit breaker)."""
    budget = RetryBudget(BudgetConfig())
    breaker = CircuitBreaker(CircuitBreakerConfig(name="substrate_parity"), budget=budget)
    policy = DefaultRetryPolicy(RetryPolicyConfig())
    return RetryOrchestrator(policy, budget, breaker, Subsystem.HTTP)


class PacedLiveParitySource:
    """DARK live-parity source (S8-armed). Composes v1's pacing controllers directly.

    Pacing path per outbound fetch (the v1 idiom): ``budget.consume()`` (per-day P10
    cap, S8-0) → ``floor_gate.admit()`` (advisory static floor) → ``semaphore.acquire()``
    (AIMD concurrency slot) → ``retry.execute_with_retry_async(...)`` (resilience) — and
    the fan-out routes ``gather_with_semaphore`` (bounded concurrency). The innermost
    outbound call is the ONLY dark seam: it raises ``LiveParityNotArmedError`` until an
    ``outbound`` implementation is injected AND ``armed=True`` (both S8 acts).

    AIMD SIGNAL (S8-0 fix): a 429 (or rate-limit equivalent) on the outbound leg calls
    ``slot.reject()`` BEFORE retry-handling — mirroring v1 (``asana_http`` :485/:633/:723)
    — so the AIMD window SHRINKS on backpressure. Without this a 429 was invisible to
    AIMD (window only ever grew), the exact self-inflicted-429-storm scar class.

    BUDGET (S8-0, optional): when a ``PerDayBudgetLedger`` is injected, EVERY upstream
    attempt (429'd included) charges it; at cap it raises ``ParityBudgetExhausted`` and
    the outbound never runs. The budget is wired through the real fetch path but arms
    nothing — the dark guard still gates all live execution.
    """

    def __init__(
        self,
        *,
        armed: bool = False,
        concurrency: int = 5,
        aimd_ceiling: int = 10,
        outbound: Callable[[ArtifactId], Awaitable[ParityObservation]] | None = None,
        gate_clock: Callable[[], float] | None = None,
        gate_sleep: Callable[[float], Awaitable[None]] | None = None,
        budget: PerDayBudgetLedger | None = None,
    ) -> None:
        self._armed = armed
        self._concurrency = concurrency
        self._semaphore = AsyncAdaptiveSemaphore(
            AIMDConfig(ceiling=aimd_ceiling), name="substrate_parity"
        )
        self._allocator = BudgetAllocator(BudgetAllocatorConfig())
        self._floor_gate = self._allocator.warmer_floor_gate(clock=gate_clock, sleep=gate_sleep)
        self._retry = _build_retry_orchestrator()
        self._outbound_impl = outbound
        self._budget = budget

    @property
    def armed(self) -> bool:
        return self._armed

    def aimd_stats(self) -> dict[str, Any]:
        """Read-only AIMD semaphore snapshot (``decrease_count`` etc.).

        The observable read-side of the S8-0 reject fix: a caller (and the
        discriminating test) can see a 429 propagate as a window decrease without
        reaching into the semaphore's privates.
        """
        return self._semaphore.get_stats()

    def routes_through_paced_primitives(self) -> bool:
        """True iff the live path is genuinely wired through all four v1 primitives.

        A structural self-check the composition test asserts — the RC-E-4 routing
        invariant is a property of the object, not a comment.
        """
        return (
            isinstance(self._semaphore, AsyncAdaptiveSemaphore)
            and self._floor_gate is not None
            and isinstance(self._retry, RetryOrchestrator)
        )

    async def _outbound(self, aid: ArtifactId) -> ParityObservation:
        if not self._armed or self._outbound_impl is None:
            raise LiveParityNotArmedError(
                "live-parity outbound fetch is DARK until S8 (arm + inject a paced "
                "outbound impl); RC-E-4 forbids any un-paced AsanaClient path here"
            )
        return await self._outbound_impl(aid)

    async def _paced_fetch_one(self, aid: ArtifactId) -> ParityObservation:
        await self._floor_gate.admit()  # (2) advisory static floor
        async with await self._semaphore.acquire() as slot:  # (1) AIMD concurrency slot

            async def _attempt() -> ParityObservation:
                if self._budget is not None:
                    # (0) charge the per-day budget for THIS attempt before the call —
                    # a 429'd/refused attempt still spent its unit; at cap this raises
                    # ParityBudgetExhausted (a plain RuntimeError core.retry treats as
                    # non-transient) and the outbound never runs.
                    self._budget.consume()
                try:
                    return await self._outbound(aid)
                except LiveParityNotArmedError:
                    raise  # dark guard: propagate verbatim (core.retry-safe RuntimeError)
                except Exception as exc:
                    # Mirror v1: a 429 shrinks the AIMD window BEFORE retry-handling.
                    rate_limited = _is_rate_limit_signal(exc)
                    if rate_limited:
                        slot.reject()  # AIMD: signal 429 -- reject BEFORE retry-handling
                    # Bridge across core.retry's botocore-shaped classifier (a raw
                    # AsanaError would AttributeError there); original kept as __cause__.
                    raise ParityOutboundError(
                        str(exc),
                        status_code=getattr(exc, "status_code", None),
                        rate_limited=rate_limited,
                    ) from exc

            result = await self._retry.execute_with_retry_async(  # (4) resilience
                _attempt,
                operation_name="substrate_parity_outbound",
            )
            slot.succeed()
            return result

    async def fetch_all_paced(self, aids: Iterable[ArtifactId]) -> list[ParityObservation]:
        """S8 entry: bounded, paced fan-out over many (project, entity) pairs."""
        coros = [self._paced_fetch_one(aid) for aid in aids]  # (3) bounded fan-out
        results = await gather_with_semaphore(
            coros,
            concurrency=self._concurrency,
            return_exceptions=False,
            label="substrate_parity",
        )
        return list(results)

    def fetch(self, aid: ArtifactId) -> ParityObservation:
        """``ParitySource`` conformance. DARK: never silently runs live in wave-2."""
        if not self._armed:
            raise LiveParityNotArmedError(
                "PacedLiveParitySource.fetch invoked while DARK (armed=False); "
                "S8 arms this after the live-parity door opens"
            )
        return asyncio.run(self._paced_fetch_one(aid))


class ParityRunner:
    """Computes v2-beside-v1 and emits a per-divergence ledger.

    ``now`` is injected (deterministic ages; no wall clock) — wave-2 fixtures pass
    the exemplar's re-warm instant.
    """

    def __init__(self, source: ParitySource, *, now: datetime) -> None:
        self._source = source
        self._now = now

    def run(self, aids: Iterable[ArtifactId]) -> list[DivergenceLedgerEntry]:
        """Fetch each (project, entity); emit a ledger entry per divergence."""
        entries: list[DivergenceLedgerEntry] = []
        for aid in aids:
            observation = self._source.fetch(aid)
            if not diverges(observation.v1, observation.v2):
                continue
            stale, fresh = order_by_age(observation.v1, observation.v2)
            payload = divergence_payload(stale, fresh, now=self._now)
            entries.append(
                DivergenceLedgerEntry(
                    artifact_key=display_key(observation.aid),
                    stale_plane=stale.plane,
                    fresh_plane=fresh.plane,
                    payload=payload,
                    explanation=explain_divergence(payload, baseline_value=stale.served_value),
                )
            )
        return entries


def display_key(aid: ArtifactId) -> str:
    """Harness-internal DISPLAY key for a (project, entity).

    NOT the storage key: ``substrate.identity.artifact_key`` raises
    ``NotImplementedError`` (owned by S3). This is a stable label for the ledger.
    """
    return f"{aid.project_gid}/{aid.entity_type.value}"


# --------------------------------------------------------- process singleton ---
_PROCESS_FETCHER: PacedLiveParitySource | None = None


def get_process_fetcher(
    *,
    concurrency: int = 5,
    aimd_ceiling: int = 10,
    budget: PerDayBudgetLedger | None = None,
) -> PacedLiveParitySource:
    """Return THE one process-wide paced fetcher (CAPACITY-s4 condition 2), idempotent.

    A fresh ``PacedLiveParitySource`` per rebuild would give each concurrent rebuild
    its OWN AIMD semaphore + bounded-gather ceiling, so K concurrent rebuilds would
    admit K × the intended in-flight ceiling — the capacity-condition-2 hazard the
    wave-2 handoff (:94-96) names before any K>1 rebuild. This factory hands every
    caller in the process the SAME instance, so the semaphore + ``gather_with_semaphore``
    width are ONE shared K>1 in-flight ceiling guard.

    [H12]: single-flight dedupes same-``ArtifactId`` in-flight; this singleton is the
    orthogonal DISTINCT-``ArtifactId`` in-flight ceiling guard (single-flight does not
    bound how many *different* artifacts rebuild concurrently — this does).

    Idempotent: the first call constructs (DARK — never armed here); subsequent calls
    return the identical object and ignore later kwargs (the ceiling is process-wide,
    not per-caller).
    """
    global _PROCESS_FETCHER
    if _PROCESS_FETCHER is None:
        _PROCESS_FETCHER = PacedLiveParitySource(
            concurrency=concurrency, aimd_ceiling=aimd_ceiling, budget=budget
        )
    return _PROCESS_FETCHER


def reset_process_fetcher() -> None:
    """Drop the process-singleton (test isolation only; never a production path)."""
    global _PROCESS_FETCHER
    _PROCESS_FETCHER = None
