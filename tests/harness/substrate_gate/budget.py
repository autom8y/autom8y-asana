"""Per-day P10 budget counter (S8-0 pre-gate hardening — capacity condition 3).

The wave-2 harness had NO enforced per-day fetch budget: ``BudgetAllocator`` /
``RetryBudget`` are 60-second, advisory, fail-OPEN windows and ``rebuild()`` takes
no budget param (wave-2 handoff :99-102). This module lands the missing HARD
precondition of the P5 cutover gate — a cross-invocation-durable per-day cap that
the live-parity / rebuild fetch path REFUSES against, loudly, never log-and-continue.

Two pieces:

  * ``PerDayBudgetLedger`` — a date-keyed JSON ledger persisted at a
    constructor-injected path with an atomic (write-temp + ``os.replace``) update
    guarded by a blocking cross-process ``flock`` (concurrent chargers serialize;
    no lost updates). ``consume(units)`` counts EVERY upstream fetch ATTEMPT (a
    429'd attempt is still an attempt against the daily API allowance) and raises
    ``ParityBudgetExhausted`` when the charge would take the day OVER the cap,
    BEFORE the attempt proceeds — never overshooting, never partially charging.
    A corrupt/tampered ledger raises ``BudgetLedgerCorrupt`` (refuse > wrong); only a
    *missing* file is a legitimate empty day. Durable across process invocations: a
    fresh ledger over the same path continues the same day's count.

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
import fcntl
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import IO

    from autom8_asana.substrate.identity import ArtifactId
    from autom8_asana.substrate.rebuild import FetchedSections, PacedAsanaFetcher

__all__ = [
    "PINNED_LEDGER_PATH",
    "BudgetLedgerCorrupt",
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


class BudgetLedgerCorrupt(RuntimeError):
    """The on-disk ledger is unreadable/tampered — parity REFUSES; a human decides.

    Raised by ``PerDayBudgetLedger._load`` when the ledger file EXISTS but does not
    parse as a JSON object of ``day -> int`` (invalid JSON, a non-dict payload, or a
    non-integer count). A *missing* file is NOT corrupt — it is a legitimate empty
    ledger (first run of the day). There is NO silent reset-to-zero and NO
    auto-quarantine: a corrupt ledger would otherwise fail OPEN (reset the day's count
    to 0 and let fetches proceed), the exact log-and-continue posture this module's
    docstring forbids. Refuse loudly so a human decides (refuse > wrong, charter P2).
    Like ``ParityBudgetExhausted`` it is a plain ``RuntimeError`` (not an
    ``Autom8Error``), so ``core.retry`` classifies it non-transient and the
    orchestrator re-raises immediately instead of retrying against a poisoned ledger.
    """


# Production ledger home consumed by WU-3 wiring (NOT by tests — the constructor takes
# an explicit path so tests pin a tmp_path). Deliberately repo-relative and durable:
# NOT /tmp (wiped on reboot) and NOT the session scratchpad (dies at park), because the
# ledger MUST survive park-per-day across the multi-day P5 cutover-parity window. The
# ``{year}`` segment bounds file growth (one date key accrues per UTC day; the in-file
# date keys already reset the daily count) — WU-3 resolves it via ``.format(year=...)``
# at arming time. The per-day cap stays constructor-injected (calibrated from the UV-P-6
# probe at WU-1); it is deliberately NOT hardcoded here.
PINNED_LEDGER_PATH = ".sos/wip/parity/budget-ledger-{year}.json"  # P13-amendable


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
            text = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}  # legitimate empty ledger — first run (of the day); NOT corrupt
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise BudgetLedgerCorrupt(
                f"parity budget ledger at {self._path} is not valid JSON — refusing "
                f"(no silent reset-to-zero); a human must inspect/repair: {exc}"
            ) from exc
        if not isinstance(raw, dict):
            raise BudgetLedgerCorrupt(
                f"parity budget ledger at {self._path} is not a JSON object "
                f"(got {type(raw).__name__}) — refusing; a human must inspect/repair"
            )
        # F-2/F-3 (WU-3): strict non-negative-int day counts. ``int(v)`` silently
        # coerced ``"7"`` -> 7, ``3.9`` -> 3 (truncated), ``True`` -> 1, and accepted a
        # NEGATIVE count that fails the budget OPEN (a ``{"day": -1000000}`` payload grants
        # ~1M attempts). Each day count MUST be a real, non-negative ``int`` (``bool`` is an
        # int subclass -> rejected first); anything else is a tampered/corrupt ledger -> refuse
        # loudly (refuse > wrong), never coerce.
        parsed: dict[str, int] = {}
        for key, value in raw.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise BudgetLedgerCorrupt(
                    f"parity budget ledger at {self._path} has a non-int/negative day count "
                    f"for {key!r} ({value!r}) — refusing (no silent coercion/reset); "
                    "a human must inspect/repair"
                )
            parsed[str(key)] = value
        return parsed

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

    def _lock_path(self) -> Path:
        return self._path.with_name(f"{self._path.name}.lock")

    def _acquire_lock(self) -> IO[str]:
        """Take a blocking cross-process exclusive lock over the load→check→write section.

        Blocking ``LOCK_EX`` (NOT the ``LOCK_NB``-then-skip of ``polling_scheduler``): a
        contending charge MUST wait its turn — skipping the lock would let it proceed
        unbudgeted (a lost update / overshoot); the section is bounded local file IO that
        cannot wedge and flock auto-releases on fd-close/process-death, so a blocking
        acquire is deadlock-free. PID-stamped for who-holds-it diagnostics.
        """
        lock_path = self._lock_path()
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = open(lock_path, "w", encoding="utf-8")  # noqa: SIM115 — held across return; released in _release_lock
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        except BaseException:
            lock_file.close()
            raise
        lock_file.write(f"{datetime.now(UTC).isoformat()}\npid={os.getpid()}\n")
        lock_file.flush()
        return lock_file

    def _release_lock(self, lock_file: IO[str]) -> None:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        finally:
            lock_file.close()  # closing also drops the flock (belt-and-suspenders)

    def consume(self, units: int = 1) -> int:
        """Charge ``units`` fetch attempt(s) against today's budget; return the new count.

        Raises ``ParityBudgetExhausted`` when the charge would take today's count OVER
        the cap (``current + units > cap``) — the charge does not proceed and NOTHING is
        written (no partial charge). For ``units == 1`` this is exactly the prior
        ``current >= cap`` boundary. Every ATTEMPT calls this, including one that will
        subsequently 429: the attempt is charged first, so a rate-limited or refused
        attempt still spends its unit. The whole read-modify-write runs under a blocking
        cross-process ``flock`` (see ``_acquire_lock``) so two processes near the cap
        serialize instead of both reading ``N < cap`` and both charging (a lost update
        that would overshoot the cap).

        ``units`` MUST be ``>= 1`` (F-1, WU-3): before this guard, ``consume(-3)`` silently
        REFUNDED the day's count (``current + (-3) > cap`` is False -> the ledger wrote a
        LOWER count) and ``consume(0)`` at cap succeeded as a no-op. Both write states the
        cap contract forbids. WU-3 computes caller-side multi-unit charges from an
        HTTP-boundary count, so a sign/arithmetic bug there must fail the meter LOUD, never
        silently refund it OPEN (mirrors the constructor's ``cap >= 1`` guard).
        """
        if units < 1:
            raise ValueError(
                f"consume(units) requires units >= 1 (got {units}); a non-positive charge "
                "would silently refund/no-op the day count and fail the P10 cap OPEN"
            )
        lock_file = self._acquire_lock()
        try:
            data = self._load()
            key = self._today_key()
            current = data.get(key, 0)
            if current + units > self._cap:
                raise ParityBudgetExhausted(
                    f"per-day parity fetch budget exhausted for {key}: "
                    f"count={current} + units={units} > cap={self._cap}; "
                    f"parity halts (no partial charge, no log-and-continue)"
                )
            data[key] = current + units
            self._atomic_write(data)
            return data[key]
        finally:
            self._release_lock(lock_file)


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
