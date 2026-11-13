"""D6 sweeper: re-drives undecided deliveries, under the reconciler lease (A3, DARK).

Design of record: TDD-asana-bench-D6-shadow-receiver-20261110 r4.10, sections 2a (the
sparse ``undecided`` index), 4 step 9, 5 steps 1 and 7, and 7 (undecided age); review
rows W F-11 (residual) and S TM-12 lease; fixtures SW-1, SW-2 and SW-2b (section 9).

Deciding runs after the 200, so a task that dies between the response and the decision
leaves a persisted, undecided row that Asana will not redeliver. The sweeper is the
backstop:

* It runs only while it holds ``LEASE#reconciler`` (S TM-12). It takes the lease with the
  reconciler's own owner, so one task runs both, and a second task skips.
* It reads the sparse ``undecided`` index, oldest first. The index is KEYS_ONLY and never
  consistent, so each row is re-read consistently, through the conditional claim.
* An ``accepted`` row older than ``ACCEPTED_GRACE_S`` is claimed. A ``claimed`` row is
  taken only once its claim is older than ``CLAIM_LEASE_S`` (2 minutes). Only the sweeper
  takes a stale claim (A C-7). A losing claimer stops.
* A delivery whose decide fails or defers is retried on later sweeps. After
  ``MAX_ATTEMPTS`` (5) it is closed as ``error/abandoned`` and counted (SW-1), so the
  section 8 criterion "the sweeper abandoned nothing" is checkable.
* Each run sets the undecided-age gauge (section 7).

With ``ACCEPTED_GRACE_S`` 30 and ``SWEEP_INTERVAL_S`` 60, a delivery whose post-response
decide never ran is decided within 2 minutes (SW-1).

DARK. :class:`Sweeper` refuses to construct unless ``ASANA_HOOK_SHADOW_ENABLED`` is
exactly ``"1"``, nothing in production constructs one, and no decider exists until A4.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from autom8y_log import get_logger

from autom8_asana.trigger.hook_environment import shadow_flag_on
from autom8_asana.trigger.hook_registry import HookRegistryError
from autom8_asana.trigger.liveness import DeliveryResult, record_undecided_age
from autom8_asana.trigger.receiver import (
    DeliveryDecider,
    ReceiverRegistryPort,
    ShadowReceiverDisabled,
    drive_delivery,
)
from autom8_asana.trigger.registration import LEASE_DURATION_S

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

logger = get_logger(__name__)

SWEEP_INTERVAL_S: Final[int] = 60
ACCEPTED_GRACE_S: Final[int] = 30
CLAIM_LEASE_S: Final[int] = 120
MAX_ATTEMPTS: Final[int] = 5
SWEEP_BATCH: Final[int] = 100


@dataclass
class SweepReport:
    ran: bool
    skipped_reason: str | None = None
    results: list[DeliveryResult] = field(default_factory=list)
    oldest_undecided_s: int = 0
    errors: list[str] = field(default_factory=list)


class Sweeper:
    """Re-drives undecided ``DLV`` rows through the decider, under the reconciler lease."""

    def __init__(
        self,
        *,
        registry: ReceiverRegistryPort,
        decider: DeliveryDecider,
        lease_owner: str,
        clock: Callable[[], float] = time.time,
        environ: Mapping[str, str] | None = None,
        interval_s: int = SWEEP_INTERVAL_S,
        lease_s: int = LEASE_DURATION_S,
    ) -> None:
        if not shadow_flag_on(os.environ if environ is None else environ):
            raise ShadowReceiverDisabled("ASANA_HOOK_SHADOW_ENABLED is not exactly '1'")
        if not lease_owner:
            raise ValueError("the sweeper needs the reconciler's lease owner")
        self._registry = registry
        self._decider = decider
        self._owner = lease_owner
        self._clock = clock
        self._interval_s = interval_s
        self._lease_s = lease_s

    async def run_once(self) -> SweepReport:
        now = int(self._clock())
        acquired = await asyncio.to_thread(
            self._registry.acquire_lease, owner=self._owner, now=now, duration_s=self._lease_s
        )
        if not acquired:
            return SweepReport(ran=False, skipped_reason="lease_held")
        report = SweepReport(ran=True)
        try:
            oldest = await asyncio.to_thread(self._registry.query_undecided, limit=1)
            due = await asyncio.to_thread(
                self._registry.query_undecided,
                received_before=now - ACCEPTED_GRACE_S + 1,
                limit=SWEEP_BATCH,
            )
        except HookRegistryError as exc:
            logger.error("hook_sweep_query_failed", extra={"error_type": type(exc).__name__})
            report.errors.append(type(exc).__name__)
            return report
        received = oldest[0][2] if oldest else None
        report.oldest_undecided_s = max(0, now - received) if received is not None else 0
        record_undecided_age(report.oldest_undecided_s)
        for handle, event_key, _received_at in due:
            report.results.append(
                await drive_delivery(
                    registry=self._registry,
                    decider=self._decider,
                    handle=handle,
                    event_key=event_key,
                    now=int(self._clock()),
                    stale_before=int(self._clock()) - CLAIM_LEASE_S,
                    max_attempts=MAX_ATTEMPTS,
                )
            )
        return report

    async def run_forever(self, stop: asyncio.Event) -> None:
        """Sweep every interval until ``stop``; the lease is released however it ends."""
        try:
            while not stop.is_set():
                await self.run_once()
                try:
                    await asyncio.wait_for(stop.wait(), timeout=self._interval_s)
                except TimeoutError:
                    continue
        finally:
            try:
                await asyncio.to_thread(self._registry.release_lease, owner=self._owner)
            except HookRegistryError as exc:
                logger.error(
                    "hook_sweep_lease_release_failed", extra={"error_type": type(exc).__name__}
                )
