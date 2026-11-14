"""D6 shadow receiver: verify a delivery, persist it, defer to the decider (A3, DARK).

Design of record: TDD-asana-bench-D6-shadow-receiver-20261110 r4.10, sections 2a, 3
(handshake), 4 (steps 1 to 9), 5 step 1 (claim) and 7 (liveness). The decision engine
(section 5 steps 2 to 8) is A4 and is not here: the receiver stores each verified event
as a ``DLV`` row and hands the claimed row to an injected :class:`DeliveryDecider`.

DARK. Nothing in production constructs a :class:`ShadowReceiver` in this PR. It refuses
to construct unless ``ASANA_HOOK_SHADOW_ENABLED`` is exactly ``"1"``;
:func:`build_shadow_receiver` returns ``None`` with the flag off before any factory is
called; and the handshake re-checks the flag on every call (warden-bench F-1). With the
flag on, a refused marker fails startup, and real DynamoDB and Secrets Manager clients
are built only on exactly ``production`` (auth-bench A3-2, in ``hook_registry`` and
``hook_store``). No decider exists until A4, so nothing can build one yet.

The delivery path, in order, all before any JSON parse (section 4):

1. Handle shape, then the in-memory index snapshot. An unknown handle is 404 and never
   reaches DynamoDB or Secrets Manager (KS-1). The snapshot is refreshed every 60 s from
   the ``PROJECT#{gid}/ACTIVE`` rows of the watched projects, off the request path.
2. ``Content-Encoding`` absent or ``identity``, else 415 (counted in the budget, A N-1).
3. Body cap, 256 KiB, else 413 before the HMAC (SZ-1).
4. ``X-Hook-Signature``: exactly one, 64 lowercase hex, on the raw bytes, else 401.
5-6. Byte compare against the cached key; at most one key read per handle per 60 s;
   a read failure is 500, never 401 (``trigger.signature``).
7. A consistent read of ``HOOK``: the state must be ``active``, else 403 (W TM-8).
8. Each event is put as ``DLV`` ``accepted``, conditionally, so a redelivery never resets
   it (A N4-2). Any failure is 500 (R-A6).
9. 200. Deciding runs after the response: claim ``accepted -> claimed`` (a losing claimer
   stops), then the decider. The sweeper is the backstop (``trigger.sweeper``).

A request carrying ``X-Hook-Secret`` is a handshake: it bypasses the snapshot and does a
consistent read behind the ``hook:handshake`` bucket (HS-3), then runs
``registration.handle_handshake``.

The handle is never logged (auth-bench A3-1); log lines carry ``handle_fp``.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Final, Protocol

from autom8y_log import get_logger

from autom8_asana.trigger.hook_environment import assert_shadow_startup, shadow_flag_on
from autom8_asana.trigger.hook_registry import (
    DeliveryRecord,
    HookRegistryConflict,
    HookRegistryError,
    HookState,
)
from autom8_asana.trigger.hook_store import handle_fingerprint
from autom8_asana.trigger.liveness import (
    DeliveryResult,
    RequestOutcome,
    record_delivery,
    record_request,
)
from autom8_asana.trigger.registration import (
    HANDLE_PATTERN,
    HandshakeReason,
    HandshakeResult,
    HookRegistryPort,
    HookStorePort,
    handle_handshake,
)
from autom8_asana.trigger.signature import (
    BodyTooLarge,
    FailureBudget,
    HeaderShape,
    SignatureVerifier,
    VerifyOutcome,
    declared_length_too_large,
    encoding_permitted,
    read_capped,
    signature_header,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Iterable, Mapping, Sequence

    from autom8_asana.trigger.watched_projects import WatchedProject

logger = get_logger(__name__)

# Where the wiring PR puts the receiver; the route reads it from ``app.state``.
RECEIVER_STATE_ATTR: Final[str] = "asana_hook_receiver"
INDEX_REFRESH_S: Final[int] = 60
# The hook:handshake bucket (section 3, TM-4 residual): handshakes bypass the snapshot, so
# they are bounded on their own. Registration creates at most one webhook per watched
# project per reconcile; ten a minute per task is ample, and a flood is alarmed.
HANDSHAKE_BUCKET_CAPACITY: Final[int] = 10
HANDSHAKE_BUCKET_REFILL_S: Final[float] = 6.0
HOOK_SECRET_HEADER: Final[bytes] = b"x-hook-secret"


class ShadowReceiverDisabled(RuntimeError):
    """Construction refused: ``ASANA_HOOK_SHADOW_ENABLED`` is not exactly ``"1"``."""


class DecideOutcome(StrEnum):
    """What the decider did with a claimed delivery."""

    DECIDED = "decided"  # the record is emitted; the row may move to `decided`
    DEFERRED = "deferred"  # another owner's live claim holds a key; retry later


@dataclass(frozen=True)
class ClaimedDelivery:
    """A claimed ``DLV`` row, handed to the decider. The row's key owns the decision keys."""

    handle: str = field(repr=False)
    event_key: str
    claim_owner: str
    attempts: int
    received_at: int
    created_at: str | None
    event: Mapping[str, Any] = field(repr=False)

    @classmethod
    def from_record(cls, record: DeliveryRecord) -> ClaimedDelivery:
        if record.claim_owner is None:
            raise HookRegistryError("a claimed delivery has no claim owner")
        return cls(
            handle=record.handle,
            event_key=record.event_key,
            claim_owner=record.claim_owner,
            attempts=record.attempts,
            received_at=record.received_at,
            created_at=record.created_at,
            event=json.loads(record.event_json),
        )


class DeliveryDecider(Protocol):
    """The A4 decision engine, as the receiver and the sweeper see it."""

    async def decide(self, delivery: ClaimedDelivery) -> DecideOutcome: ...


class ReceiverRegistryPort(HookRegistryPort, Protocol):
    def put_delivery(
        self,
        *,
        handle: str,
        event_key: str,
        event_json: str,
        created_at: str | None,
        now: int,
    ) -> bool: ...
    def get_delivery(
        self, handle: str, event_key: str, *, consistent: bool = True
    ) -> DeliveryRecord | None: ...
    def claim_delivery(
        self,
        *,
        handle: str,
        event_key: str,
        owner: str,
        now: int,
        stale_before: int | None = None,
    ) -> DeliveryRecord | None: ...
    def mark_delivery_decided(
        self,
        *,
        handle: str,
        event_key: str,
        owner: str,
        now: int,
        outcome: str | None = None,
    ) -> None: ...
    def query_undecided(
        self, *, received_before: int | None = None, limit: int = 100
    ) -> list[tuple[str, str, int | None]]: ...
    def touch_liveness(self, *, project_gid: str, now: int, heartbeat: bool) -> None: ...


class ReceiverStorePort(HookStorePort, Protocol):
    def read_hook_value(self, *, handle: str) -> str: ...


def canonical_event_json(event: Mapping[str, Any]) -> str:
    """One event as canonical JSON: sorted keys, no spaces, ASCII. Stable across batches."""
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def event_key(event_json: str) -> str:
    """The ``DLV`` sort key: SHA-256 of the canonical event JSON (section 2a)."""
    return hashlib.sha256(event_json.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class PersistedDelivery:
    handle: str = field(repr=False)
    event_key: str
    created: bool


@dataclass(frozen=True)
class ReceiveResult:
    status_code: int
    outcome: RequestOutcome
    deliveries: tuple[PersistedDelivery, ...] = ()
    echo: str | None = field(default=None, repr=False)


_STATUS: Final[dict[RequestOutcome, int]] = {
    RequestOutcome.SHADOW_OFF: 404,
    RequestOutcome.UNKNOWN_HANDLE: 404,
    RequestOutcome.ENCODING_REFUSED: 415,
    RequestOutcome.TOO_LARGE: 413,
    RequestOutcome.SIGNATURE_INVALID: 401,
    RequestOutcome.SIGNATURE_MISMATCH: 401,
    RequestOutcome.KEY_UNAVAILABLE: 500,
    RequestOutcome.REGISTRY_UNAVAILABLE: 500,
    RequestOutcome.NOT_ACTIVE: 403,
    RequestOutcome.BODY_INVALID: 400,
    RequestOutcome.PERSIST_FAILED: 500,
    RequestOutcome.ACCEPTED: 200,
    RequestOutcome.HEARTBEAT: 200,
    RequestOutcome.HANDSHAKE_THROTTLED: 429,
}


class HandshakeBucket:
    """A token bucket for the handshake path (``hook:handshake``)."""

    def __init__(
        self,
        *,
        capacity: int = HANDSHAKE_BUCKET_CAPACITY,
        refill_s: float = HANDSHAKE_BUCKET_REFILL_S,
    ) -> None:
        self._capacity = float(capacity)
        self._refill_s = refill_s
        self._tokens = float(capacity)
        self._at: float | None = None

    def take(self, now: float) -> bool:
        if self._at is not None:
            self._tokens = min(self._capacity, self._tokens + (now - self._at) / self._refill_s)
        self._at = now
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False


def _events(body: bytes) -> list[Mapping[str, Any]] | None:
    """The ``events`` array of a verified body, or ``None`` when the body is not one."""
    try:
        parsed = json.loads(body)
    except ValueError:
        return None
    if not isinstance(parsed, dict):
        return None
    events = parsed.get("events")
    if not isinstance(events, list) or not all(isinstance(e, dict) for e in events):
        return None
    return events


class ShadowReceiver:
    """Verifies and persists Asana deliveries for active hooks, and answers handshakes."""

    def __init__(
        self,
        *,
        registry: ReceiverRegistryPort,
        store: ReceiverStorePort,
        decider: DeliveryDecider,
        project_gids: Sequence[str],
        clock: Callable[[], float] = time.time,
        environ: Mapping[str, str] | None = None,
        handshake_bucket: HandshakeBucket | None = None,
        budget: FailureBudget | None = None,
    ) -> None:
        self._environ: Mapping[str, str] = os.environ if environ is None else environ
        if not shadow_flag_on(self._environ):
            raise ShadowReceiverDisabled("ASANA_HOOK_SHADOW_ENABLED is not exactly '1'")
        self._registry = registry
        self._store = store
        self._decider = decider
        self._project_gids = tuple(project_gids)
        self._clock = clock
        self._bucket = handshake_bucket or HandshakeBucket()
        self.verifier = SignatureVerifier(read_key=self._read_key, budget=budget)
        self._index: frozenset[str] = frozenset()
        self._index_loaded_at: int | None = None

    def _now(self) -> int:
        return int(self._clock())

    async def _read_key(self, handle: str) -> str:
        return await asyncio.to_thread(self._store.read_hook_value, handle=handle)

    # -- the index snapshot --------------------------------------------------------

    @property
    def index_loaded_at(self) -> int | None:
        return self._index_loaded_at

    def knows(self, handle: str) -> bool:
        return handle in self._index

    async def refresh_index(self) -> int:
        """Rebuild the snapshot from each watched project's ``ACTIVE`` row.

        Raises :class:`HookRegistryError` on any read failure, so the first load at
        startup fails loudly; the periodic refresh keeps the last snapshot instead.
        """
        handles: set[str] = set()
        for gid in self._project_gids:
            handle = await asyncio.to_thread(self._registry.get_active_handle, gid, consistent=True)
            if handle is not None and HANDLE_PATTERN.fullmatch(handle):
                handles.add(handle)
        self._index = frozenset(handles)
        self._index_loaded_at = self._now()
        return len(self._index)

    async def run_index_refresh(self, stop: asyncio.Event) -> None:
        """Refresh every ``INDEX_REFRESH_S`` until ``stop``. A failure keeps the last snapshot."""
        while not stop.is_set():
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=INDEX_REFRESH_S)
            if stop.is_set():
                return
            try:
                await self.refresh_index()
            except HookRegistryError as exc:
                logger.error("hook_index_refresh_failed", extra={"error_type": type(exc).__name__})

    # -- handshake (section 3) -----------------------------------------------------

    async def handshake(self, *, handle: str, hook_header: str | None) -> ReceiveResult:
        """Answer a handshake. Zero registry or store calls unless the flag is exactly "1"."""
        if not shadow_flag_on(self._environ):
            record_request(RequestOutcome.SHADOW_OFF)
            return ReceiveResult(404, RequestOutcome.SHADOW_OFF)
        if not HANDLE_PATTERN.fullmatch(handle):
            record_request(RequestOutcome.UNKNOWN_HANDLE)
            return ReceiveResult(404, RequestOutcome.UNKNOWN_HANDLE)
        fp = handle_fingerprint(handle)
        if not self._bucket.take(self._clock()):
            record_request(RequestOutcome.HANDSHAKE_THROTTLED, handle_fp=fp)
            return ReceiveResult(429, RequestOutcome.HANDSHAKE_THROTTLED)
        try:
            result: HandshakeResult = await handle_handshake(
                handle=handle,
                hook_header=hook_header,
                registry=self._registry,
                store=self._store,
                now=self._now(),
            )
        except HookRegistryError as exc:
            logger.error(
                "hook_handshake_registry_failed",
                extra={"handle_fp": fp, "error_type": type(exc).__name__},
            )
            record_request(RequestOutcome.REGISTRY_UNAVAILABLE, handle_fp=fp)
            return ReceiveResult(500, RequestOutcome.REGISTRY_UNAVAILABLE)
        if result.status_code == 200:
            record_request(RequestOutcome.HANDSHAKE_ECHOED, handle_fp=fp)
            return ReceiveResult(200, RequestOutcome.HANDSHAKE_ECHOED, echo=result.echo)
        if result.reason is HandshakeReason.SECOND_HANDSHAKE:
            outcome = RequestOutcome.HANDSHAKE_COMPROMISED
        elif result.reason is HandshakeReason.STORE_FAILED:
            outcome = RequestOutcome.HANDSHAKE_STORE_FAILED
        elif result.reason is HandshakeReason.UNKNOWN_HANDLE:
            outcome = RequestOutcome.UNKNOWN_HANDLE
        else:
            outcome = RequestOutcome.HANDSHAKE_REFUSED
        record_request(outcome, handle_fp=fp)
        return ReceiveResult(result.status_code, outcome)

    # -- delivery (section 4) ------------------------------------------------------

    def _refuse(self, outcome: RequestOutcome, handle: str | None = None) -> ReceiveResult:
        record_request(outcome, handle_fp=None if handle is None else handle_fingerprint(handle))
        return ReceiveResult(_STATUS[outcome], outcome)

    async def receive(
        self,
        *,
        handle: str,
        raw_headers: Iterable[tuple[bytes, bytes]],
        body: AsyncIterator[bytes],
    ) -> ReceiveResult:
        """Steps 1 to 8 of section 4. Never parses JSON before the signature verifies."""
        if not shadow_flag_on(self._environ):
            return self._refuse(RequestOutcome.SHADOW_OFF)
        # Step 1: shape, then the snapshot. Unknown handles touch nothing (KS-1).
        if not HANDLE_PATTERN.fullmatch(handle) or handle not in self._index:
            return self._refuse(RequestOutcome.UNKNOWN_HANDLE)
        headers = list(raw_headers)
        now = self._now()
        budget = self.verifier.budget
        # Step 2: encoding (415, counted in the budget, A N-1).
        if not encoding_permitted(headers):
            budget.spend(handle, now)
            return self._refuse(RequestOutcome.ENCODING_REFUSED, handle)
        # Step 3: size, before any HMAC (SZ-1).
        if declared_length_too_large(headers):
            budget.spend(handle, now)
            return self._refuse(RequestOutcome.TOO_LARGE, handle)
        try:
            raw = await read_capped(body)
        except BodyTooLarge:
            budget.spend(handle, now)
            return self._refuse(RequestOutcome.TOO_LARGE, handle)
        # Step 4: header shape on the raw bytes; never a key read on a bad shape.
        shape, signature = signature_header(headers)
        if shape is not HeaderShape.OK:
            budget.spend(handle, now)
            return self._refuse(RequestOutcome.SIGNATURE_INVALID, handle)
        # Steps 5 and 6.
        verdict = await self.verifier.verify(handle, raw, signature, now)
        if verdict is VerifyOutcome.KEY_UNAVAILABLE:
            return self._refuse(RequestOutcome.KEY_UNAVAILABLE, handle)
        if verdict is not VerifyOutcome.MATCH:
            return self._refuse(RequestOutcome.SIGNATURE_MISMATCH, handle)
        # Step 7: the hook must be active right now (consistent read; W TM-8, S C5).
        try:
            record = await asyncio.to_thread(self._registry.get_hook, handle, consistent=True)
        except HookRegistryError:
            return self._refuse(RequestOutcome.REGISTRY_UNAVAILABLE, handle)
        if record is None or record.state is not HookState.ACTIVE:
            return self._refuse(RequestOutcome.NOT_ACTIVE, handle)
        events = _events(raw)
        if events is None:
            return self._refuse(RequestOutcome.BODY_INVALID, handle)
        fp = handle_fingerprint(handle)
        if not events:
            await self._touch(record.resource_gid, now, heartbeat=True, handle_fp=fp)
            record_request(RequestOutcome.HEARTBEAT, handle_fp=fp)
            return ReceiveResult(200, RequestOutcome.HEARTBEAT)
        # Step 8: one conditional put per event; any failure is 500 (R-A6).
        persisted: list[PersistedDelivery] = []
        for event in events:
            event_json = canonical_event_json(event)
            key = event_key(event_json)
            created_at = event.get("created_at")
            try:
                created = await asyncio.to_thread(
                    self._registry.put_delivery,
                    handle=handle,
                    event_key=key,
                    event_json=event_json,
                    created_at=created_at if isinstance(created_at, str) else None,
                    now=now,
                )
            except HookRegistryError:
                return self._refuse(RequestOutcome.PERSIST_FAILED, handle)
            persisted.append(PersistedDelivery(handle=handle, event_key=key, created=created))
            record_delivery(
                DeliveryResult.PERSISTED if created else DeliveryResult.REDELIVERED, handle_fp=fp
            )
        await self._touch(record.resource_gid, now, heartbeat=False, handle_fp=fp)
        record_request(RequestOutcome.ACCEPTED, handle_fp=fp)
        return ReceiveResult(200, RequestOutcome.ACCEPTED, deliveries=tuple(persisted))

    async def _touch(self, project_gid: str, now: int, *, heartbeat: bool, handle_fp: str) -> None:
        """Liveness clocks (section 7). A failed write is logged; the delivery stands."""
        try:
            await asyncio.to_thread(
                self._registry.touch_liveness,
                project_gid=project_gid,
                now=now,
                heartbeat=heartbeat,
            )
        except HookRegistryError as exc:
            logger.error(
                "hook_liveness_write_failed",
                extra={"handle_fp": handle_fp, "error_type": type(exc).__name__},
            )

    # -- after the response (section 5 step 1) -------------------------------------

    async def decide_after_response(self, deliveries: Sequence[PersistedDelivery]) -> None:
        """Claim each delivery and hand it to the decider. Never raises.

        Only ``accepted`` rows are claimed here. A row another owner claimed, live or
        stale, is left alone: only the sweeper takes a stale claim (A C-7, SW-2b).
        """
        for delivery in deliveries:
            await drive_delivery(
                registry=self._registry,
                decider=self._decider,
                handle=delivery.handle,
                event_key=delivery.event_key,
                now=self._now(),
                stale_before=None,
            )


async def drive_delivery(
    *,
    registry: ReceiverRegistryPort,
    decider: DeliveryDecider,
    handle: str,
    event_key: str,
    now: int,
    stale_before: int | None,
    max_attempts: int | None = None,
) -> DeliveryResult:
    """Claim one delivery, decide it, and close it. Shared by the receiver and sweeper.

    ``stale_before`` lets the sweeper take a claim older than the lease. When
    ``max_attempts`` is given and the claim's attempt count has reached it after a failed
    or deferred decide, the row is closed as ``error/abandoned`` (SW-1). Never raises.
    """
    fp = handle_fingerprint(handle)
    owner = uuid.uuid4().hex
    try:
        claimed = await asyncio.to_thread(
            registry.claim_delivery,
            handle=handle,
            event_key=event_key,
            owner=owner,
            now=now,
            stale_before=stale_before,
        )
    except HookRegistryError as exc:
        logger.error("hook_claim_failed", extra={"handle_fp": fp, "error_type": type(exc).__name__})
        record_delivery(DeliveryResult.DECIDE_FAILED, handle_fp=fp)
        return DeliveryResult.DECIDE_FAILED
    if claimed is None:
        record_delivery(DeliveryResult.CLAIM_LOST, handle_fp=fp)
        return DeliveryResult.CLAIM_LOST
    try:
        delivery = ClaimedDelivery.from_record(claimed)
        outcome = await decider.decide(delivery)
    except Exception as exc:  # noqa: BLE001
        # BROAD-CATCH: isolation -- a decider failure leaves the row claimed; the sweeper
        # re-drives it after the lease. It never escapes into the response cycle.
        logger.error(
            "hook_decide_failed",
            extra={
                "handle_fp": fp,
                "attempts": claimed.attempts,
                "error_type": type(exc).__name__,
            },
        )
        outcome = None
    if outcome is DecideOutcome.DECIDED:
        try:
            await asyncio.to_thread(
                registry.mark_delivery_decided,
                handle=handle,
                event_key=event_key,
                owner=owner,
                now=now,
            )
        except HookRegistryConflict:
            # Another claimer took the row after this claim went stale; it decides again
            # and the decision keys (A4) make that a duplicate, never a second decision.
            logger.warning("hook_decided_mark_conflict", extra={"handle_fp": fp})
        except HookRegistryError as exc:
            logger.error(
                "hook_decided_mark_failed",
                extra={"handle_fp": fp, "error_type": type(exc).__name__},
            )
        record_delivery(DeliveryResult.DECIDED, handle_fp=fp, attempts=claimed.attempts)
        return DeliveryResult.DECIDED
    if max_attempts is not None and claimed.attempts >= max_attempts:
        return await _abandon(registry, handle, event_key, owner, now, fp, claimed.attempts)
    if outcome is DecideOutcome.DEFERRED:
        result = DeliveryResult.DEFERRED
    else:
        result = DeliveryResult.DECIDE_FAILED
    record_delivery(result, handle_fp=fp, attempts=claimed.attempts)
    return result


ABANDONED_OUTCOME: Final[str] = "error/abandoned"


async def _abandon(
    registry: ReceiverRegistryPort,
    handle: str,
    event_key: str,
    owner: str,
    now: int,
    fp: str,
    attempts: int,
) -> DeliveryResult:
    try:
        await asyncio.to_thread(
            registry.mark_delivery_decided,
            handle=handle,
            event_key=event_key,
            owner=owner,
            now=now,
            outcome=ABANDONED_OUTCOME,
        )
    except HookRegistryError as exc:
        logger.error(
            "hook_abandon_mark_failed", extra={"handle_fp": fp, "error_type": type(exc).__name__}
        )
        record_delivery(DeliveryResult.DECIDE_FAILED, handle_fp=fp, attempts=attempts)
        return DeliveryResult.DECIDE_FAILED
    record_delivery(DeliveryResult.ABANDONED, handle_fp=fp, attempts=attempts)
    return DeliveryResult.ABANDONED


def build_shadow_receiver(
    *,
    environ: Mapping[str, str] | None = None,
    registry_factory: Callable[[], ReceiverRegistryPort],
    store_factory: Callable[[], ReceiverStorePort],
    decider_factory: Callable[[], DeliveryDecider],
    projects_factory: Callable[[], Sequence[WatchedProject]],
    clock: Callable[[], float] = time.time,
) -> ShadowReceiver | None:
    """The one entry point. With the shadow flag off it returns ``None`` and calls nothing.

    With the flag on, a refused marker raises (startup fails, section 2a), and only then
    are the factories called. A factory that fails (for example DynamoDB construction)
    raises too: startup fails, and the receiver never degrades to a noop (W F-4, R-A6).
    The caller awaits :meth:`ShadowReceiver.refresh_index` once before serving; a failed
    first load also fails startup.
    """
    env = os.environ if environ is None else environ
    if assert_shadow_startup(env) is None:
        logger.info("hook_receiver_shadow_off")
        return None
    registry = registry_factory()
    store = store_factory()
    decider = decider_factory()
    projects = projects_factory()
    return ShadowReceiver(
        registry=registry,
        store=store,
        decider=decider,
        project_gids=[p.project_gid for p in projects],
        clock=clock,
        environ=env,
    )
