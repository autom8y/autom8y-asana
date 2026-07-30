"""Per-day P10 budget counter (S8-0 pre-gate hardening — capacity condition 3).

The wave-2 harness had NO enforced per-day fetch budget: ``BudgetAllocator`` /
``RetryBudget`` are 60-second, advisory, fail-OPEN windows and ``rebuild()`` takes
no budget param (wave-2 handoff :99-102). This module lands the missing HARD
precondition of the P5 cutover gate — a cross-invocation-durable per-day cap that
the live-parity / rebuild fetch path REFUSES against, loudly, never log-and-continue.

Two pieces:

  * ``PerDayBudgetLedger`` — a date-keyed JSON ledger persisted at a
    constructor-injected path with an atomic (write-temp + ``os.replace``) update.
    ``consume()`` counts EVERY upstream fetch ATTEMPT (a 429'd attempt is still an
    attempt against the daily API allowance) and raises ``ParityBudgetExhausted``
    at/over the cap BEFORE the attempt proceeds. Durable across process
    invocations: a fresh ledger over the same path continues the same day's count.

  * ``BudgetedPacedFetcher`` — a wrapper that IMPLEMENTS the FROZEN
    ``substrate.rebuild.PacedAsanaFetcher`` Protocol (imported, never modified) by
    COMPOSING an inner ``PacedAsanaFetcher`` + a ``PerDayBudgetLedger``. Every
    ``fetch()`` consumes budget BEFORE delegating, so an inner attempt that then
    raises ``FetchRefused`` / a 429 still spent its budget unit.

The live leg stays DARK behind ``parity.LiveParityNotArmedError``; this module wires
the budget through the fetch path (real, not ornamental) without arming anything.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from autom8_asana.substrate.identity import ArtifactId
    from autom8_asana.substrate.rebuild import FetchedSections, PacedAsanaFetcher

__all__ = [
    "BudgetedPacedFetcher",
    "ParityBudgetExhausted",
    "PerDayBudgetLedger",
]


class ParityBudgetExhausted(RuntimeError):
    """The per-day fetch budget is at/over cap — parity HALTS loudly (never continues).

    A dedicated loud type (not a bare ``RuntimeError`` at the call site) so the
    cutover-gate operator can distinguish a budget stop from any other refusal, and
    so it is NOT swallowed by the ``core.retry`` transient classifier (it is not an
    ``Autom8Error`` → non-transient → the orchestrator re-raises it immediately).
    """


class PerDayBudgetLedger:
    """Cross-invocation-durable per-day fetch-attempt cap (date-keyed JSON ledger).

    The ledger file maps ``"YYYY-MM-DD" -> attempts_consumed_that_day``. ``consume``
    is read-modify-write with an atomic rename, so a crash mid-write cannot corrupt
    the prior day's count. ``clock`` is injected (default: real UTC now) so tests
    pin the day deterministically.
    """

    def __init__(
        self,
        *,
        path: str | os.PathLike[str],
        cap: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if cap < 1:
            raise ValueError(f"cap must be >= 1 (got {cap})")
        self._path = Path(path)
        self._cap = cap
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def cap(self) -> int:
        return self._cap

    def _today_key(self) -> str:
        return self._clock().date().isoformat()

    def _load(self) -> dict[str, int]:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
        if not isinstance(raw, dict):
            return {}
        return {str(k): int(v) for k, v in raw.items()}

    def _atomic_write(self, data: dict[str, int]) -> None:
        """Write ``data`` durably: temp file in the target dir, then atomic rename."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self._path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, sort_keys=True)
            os.replace(tmp, self._path)  # atomic on POSIX; never a torn ledger
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp)
            raise

    def count_today(self) -> int:
        """Attempts already consumed for the current UTC day (durable across instances)."""
        return self._load().get(self._today_key(), 0)

    def consume(self, units: int = 1) -> int:
        """Charge ``units`` fetch attempt(s) against today's budget; return the new count.

        Raises ``ParityBudgetExhausted`` when today's count is already AT the cap
        (``current >= cap``) — the charge does not proceed. Every ATTEMPT calls this,
        including one that will subsequently 429: the attempt is charged first, so a
        rate-limited or refused attempt still spends its unit.
        """
        data = self._load()
        key = self._today_key()
        current = data.get(key, 0)
        if current >= self._cap:
            raise ParityBudgetExhausted(
                f"per-day parity fetch budget exhausted for {key}: "
                f"count={current} >= cap={self._cap}; parity halts (no log-and-continue)"
            )
        data[key] = current + units
        self._atomic_write(data)
        return data[key]


class BudgetedPacedFetcher:
    """A budget-gated ``PacedAsanaFetcher`` — the real (not ornamental) integration point.

    IMPLEMENTS the FROZEN ``substrate.rebuild.PacedAsanaFetcher`` Protocol by
    COMPOSING an inner paced fetcher and a ``PerDayBudgetLedger``. ``fetch`` charges
    the ledger BEFORE delegating, so an inner ``FetchRefused`` / 429 still consumed
    its daily unit (the API allowance was already spent on the attempt). At cap the
    charge itself raises ``ParityBudgetExhausted`` and the inner fetch never runs.
    """

    def __init__(self, inner: PacedAsanaFetcher, ledger: PerDayBudgetLedger) -> None:
        self._inner = inner
        self._ledger = ledger

    async def fetch(self, aid: ArtifactId) -> FetchedSections:
        """``PacedAsanaFetcher`` conformance: charge the attempt, then delegate."""
        self._ledger.consume()  # every ATTEMPT counts (429'd included); raises at cap
        return await self._inner.fetch(aid)
