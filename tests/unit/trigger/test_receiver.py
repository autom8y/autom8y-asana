"""D6 receiver (A3): section 4 steps 1-9, the handshake path, the claim, the builder.

Design of record: TDD-asana-bench-D6-shadow-receiver-20261110 r4.10, sections 2a, 3, 4,
5 step 1 and 7. Fixtures (section 9) proved here, at the receiver: HS-1 to HS-4 (through
the receiver), KS-1, R-A1, ENC-1, SZ-1, SM-1, R-A6, DUP-1, DUP-2a and DUP-2b (the receiver
half, see below); review rows W F-1, W F-4, W F-11, A N4-2, W TM-8 step 7, A C-8, A N-1;
auth-bench A3-1 and A3-2.

DynamoDB is moto through the real ``HookRegistry`` expressions; the key store is the
in-memory test adapter; the decider is a recorder. Nothing reaches AWS or Asana, and
every handle, gid and hook value is generated at runtime.

DUP-1, DUP-2a and DUP-2b, the receiver half. "One decision" across two webhooks, and
"two decisions, no double count" across complete-reopen-complete, are made by the A4
decision keys (section 5 step 7), which are not in this PR. What the receiver owes them
is proved here: every distinct event becomes its own delivery row, an identical
redelivery never does, the same event through two webhooks reaches the decider once per
webhook carrying byte-identical canonical JSON, and no delivery is ever dropped or
merged before the keys see it.
"""

from __future__ import annotations

import json
import secrets
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from autom8_asana.trigger import hook_registry as hook_registry_module
from autom8_asana.trigger import hook_store as hook_store_module
from autom8_asana.trigger import liveness as liveness_module
from autom8_asana.trigger import receiver as receiver_module
from autom8_asana.trigger import registration as registration_module
from autom8_asana.trigger.hook_environment import HookEnvironmentRefused
from autom8_asana.trigger.hook_registry import (
    DeliveryState,
    HookRegistry,
    HookRegistryUnavailable,
    HookState,
)
from autom8_asana.trigger.hook_store import HookStore, HookStoreRefused
from autom8_asana.trigger.liveness import RequestOutcome
from autom8_asana.trigger.receiver import (
    DecideOutcome,
    ShadowReceiver,
    ShadowReceiverDisabled,
    build_shadow_receiver,
    canonical_event_json,
    event_key,
)
from tests.unit.trigger.adapters import InMemoryHookRegistry, InMemoryKeyHookStore
from tests.unit.trigger.conftest import (
    SHADOW_TEST_ENV,
    ActiveHook,
    CallCounter,
    FakeClock,
    LogSpy,
    RecordingDecider,
    batch,
    body_stream,
    completion_event,
    make_active_hook,
    runtime_gid,
    runtime_hook_value,
    sign,
)
from tests.unit.trigger.test_hook_marker import TASK_ROLE_ENV

OFF_VALUES = [None, "", "0", "true", "TRUE", "yes", "1 ", " 1", "1\n", "01"]


def _env(flag: str | None) -> dict[str, str]:
    env = {"ASANA_HOOK_ENVIRONMENT": "test"}
    if flag is not None:
        env["ASANA_HOOK_SHADOW_ENABLED"] = flag
    return env


def _receiver(
    registry: Any,
    store: Any,
    clock: FakeClock,
    *,
    decider: Any = None,
    project_gids: list[str] | None = None,
    environ: dict[str, str] | None = None,
) -> ShadowReceiver:
    return ShadowReceiver(
        registry=registry,
        store=store,
        decider=decider or RecordingDecider(),
        project_gids=project_gids or [],
        clock=clock,
        environ=dict(SHADOW_TEST_ENV) if environ is None else environ,
    )


async def _ready(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock, **kw: Any
) -> tuple[ShadowReceiver, ActiveHook]:
    hook = make_active_hook(registry, store, clock)
    receiver = _receiver(registry, store, clock, project_gids=[hook.project_gid], **kw)
    assert await receiver.refresh_index() == 1
    return receiver, hook


async def _deliver(
    receiver: ShadowReceiver,
    handle: str,
    body: bytes,
    *,
    signature: str | None = None,
    extra: list[tuple[bytes, bytes]] | None = None,
    chunks: list[bytes] | None = None,
) -> Any:
    headers: list[tuple[bytes, bytes]] = []
    if signature is not None:
        headers.append((b"x-hook-signature", signature.encode("latin-1")))
    headers += extra or []
    return await receiver.receive(
        handle=handle, raw_headers=headers, body=body_stream(*(chunks or [body]))
    )


# ---------------------------------------------------------------------------
# Construction and the flag (W F-1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("flag", OFF_VALUES)
def test_receiver_refuses_to_construct_unless_flag_is_exactly_one(
    flag: str | None, registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """W F-1 (D6 TDD fixture or review id)."""
    with pytest.raises(ShadowReceiverDisabled):
        _receiver(registry, store, clock, environ=_env(flag))


def test_receiver_constructs_when_flag_is_exactly_one(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """W F-1 twin (D6 TDD fixture or review id)."""
    assert isinstance(_receiver(registry, store, clock, environ=_env("1")), ShadowReceiver)


@pytest.mark.parametrize("flag", OFF_VALUES)
async def test_handshake_with_flag_off_makes_zero_registry_or_store_calls(
    flag: str | None,
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    clock: FakeClock,
    hex_handle: str,
) -> None:
    """W F-1: warden-bench F-1: the handshake refuses unless the flag is exactly "1"."""
    registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=int(clock()))
    counted_registry, counted_store = CallCounter(registry), CallCounter(store)
    environ = _env("1")
    receiver = _receiver(counted_registry, counted_store, clock, environ=environ)
    # The flag is read on every call, not only at construction.
    if flag is None:
        del environ["ASANA_HOOK_SHADOW_ENABLED"]
    else:
        environ["ASANA_HOOK_SHADOW_ENABLED"] = flag
    result = await receiver.handshake(handle=hex_handle, hook_header=runtime_hook_value())
    assert (result.status_code, result.outcome, result.echo) == (
        404,
        RequestOutcome.SHADOW_OFF,
        None,
    )
    assert counted_registry.calls == [] and counted_store.calls == []
    delivery = await _deliver(receiver, hex_handle, batch(), signature="a" * 64)
    assert delivery.status_code == 404
    assert counted_registry.calls == [] and counted_store.calls == []
    record = registry.get_hook(hex_handle)
    assert record is not None and record.state is HookState.PENDING


async def test_handshake_with_flag_on_echoes_through_the_same_receiver(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock, hex_handle: str
) -> None:
    """W F-1 twin (D6 TDD fixture or review id)."""
    registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=int(clock()))
    counted_registry = CallCounter(registry)
    receiver = _receiver(counted_registry, store, clock)
    value = runtime_hook_value()
    result = await receiver.handshake(handle=hex_handle, hook_header=value)
    assert (result.status_code, result.echo) == (200, value)
    assert "get_hook" in counted_registry.calls and "mark_handshaken" in counted_registry.calls


# ---------------------------------------------------------------------------
# Handshake through the receiver: HS-1 to HS-4, the bucket
# ---------------------------------------------------------------------------


async def test_handshake_bypasses_the_index_snapshot(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock, hex_handle: str
) -> None:
    """HS-3: the index snapshot lacks the handle, and the handshake still resolves."""
    receiver = _receiver(registry, store, clock)
    assert await receiver.refresh_index() == 0
    assert not receiver.knows(hex_handle)
    registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=int(clock()))
    value = runtime_hook_value()
    result = await receiver.handshake(handle=hex_handle, hook_header=value)
    assert (result.status_code, result.outcome, result.echo) == (
        200,
        RequestOutcome.HANDSHAKE_ECHOED,
        value,
    )
    assert store.has_value(hex_handle)


async def test_handshake_refuses_unknown_expired_and_active_handles_without_echo(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock, hex_handle: str
) -> None:
    """HS-1 (D6 TDD fixture or review id)."""
    receiver = _receiver(registry, store, clock)
    unknown = await receiver.handshake(handle=hex_handle, hook_header=runtime_hook_value())
    assert (unknown.status_code, unknown.echo) == (404, None)
    malformed = await receiver.handshake(handle="not-a-handle", hook_header=runtime_hook_value())
    assert (malformed.status_code, malformed.echo) == (404, None)

    registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=int(clock()))
    clock.now += 61
    expired = await receiver.handshake(handle=hex_handle, hook_header=runtime_hook_value())
    assert (expired.status_code, expired.outcome, expired.echo) == (
        403,
        RequestOutcome.HANDSHAKE_REFUSED,
        None,
    )

    hook = make_active_hook(registry, store, clock)
    active = await receiver.handshake(handle=hook.handle, hook_header=runtime_hook_value())
    assert (active.status_code, active.echo) == (403, None)


async def test_second_handshake_marks_the_hook_compromised(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock, hex_handle: str
) -> None:
    """HS-2 (D6 TDD fixture or review id)."""
    receiver = _receiver(registry, store, clock)
    registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=int(clock()))
    first = await receiver.handshake(handle=hex_handle, hook_header=runtime_hook_value())
    second = await receiver.handshake(handle=hex_handle, hook_header=runtime_hook_value())
    assert first.status_code == 200
    assert (second.status_code, second.outcome, second.echo) == (
        403,
        RequestOutcome.HANDSHAKE_COMPROMISED,
        None,
    )
    record = registry.get_hook(hex_handle)
    assert record is not None and record.state is HookState.COMPROMISED


async def test_handshake_store_failure_is_500_and_marks_failed(
    registry: InMemoryHookRegistry, clock: FakeClock, hex_handle: str
) -> None:
    """HS-4 (D6 TDD fixture or review id)."""
    failing = InMemoryKeyHookStore(environ={"ASANA_HOOK_ENVIRONMENT": "test"}, fail_create=True)
    receiver = _receiver(registry, failing, clock)
    registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=int(clock()))
    result = await receiver.handshake(handle=hex_handle, hook_header=runtime_hook_value())
    assert (result.status_code, result.outcome, result.echo) == (
        500,
        RequestOutcome.HANDSHAKE_STORE_FAILED,
        None,
    )
    record = registry.get_hook(hex_handle)
    assert record is not None and record.state is HookState.FAILED


async def test_handshake_bucket_bounds_the_snapshot_bypass(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """hook:handshake: past the bucket, a handshake is 429 and reads nothing."""
    counted = CallCounter(registry)
    receiver = _receiver(counted, store, clock)
    statuses = [
        (await receiver.handshake(handle=secrets.token_hex(16), hook_header="x" * 20)).status_code
        for _ in range(10)
    ]
    assert statuses == [404] * 10
    reads_before = len(counted.calls)
    throttled = await receiver.handshake(handle=secrets.token_hex(16), hook_header="x" * 20)
    assert (throttled.status_code, throttled.outcome) == (429, RequestOutcome.HANDSHAKE_THROTTLED)
    assert len(counted.calls) == reads_before
    clock.now += 6
    refilled = await receiver.handshake(handle=secrets.token_hex(16), hook_header="x" * 20)
    assert refilled.status_code == 404, "twin: the bucket refills"


# ---------------------------------------------------------------------------
# Delivery: steps 1 to 9
# ---------------------------------------------------------------------------


async def test_unknown_handles_never_reach_dynamodb_or_the_store(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """KS-1 (D6 TDD fixture or review id)."""
    hook = make_active_hook(registry, store, clock)
    counted_registry, counted_store = CallCounter(registry), CallCounter(store)
    receiver = _receiver(counted_registry, counted_store, clock, project_gids=[hook.project_gid])
    await receiver.refresh_index()
    counted_registry.calls.clear()
    body = batch(completion_event())
    for _ in range(1000):
        result = await _deliver(receiver, secrets.token_hex(16), body, signature="a" * 64)
        assert (result.status_code, result.outcome) == (404, RequestOutcome.UNKNOWN_HANDLE)
    assert counted_registry.calls == [] and counted_store.calls == []
    # Twin: the known handle does reach them.
    ok = await _deliver(receiver, hook.handle, body, signature=sign(hook.hook_value, body))
    assert ok.status_code == 200 and "read_hook_value" in counted_store.calls


async def test_a_thousand_mismatches_on_one_handle_cost_at_most_one_key_read(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """KS-1 (D6 TDD fixture or review id)."""
    receiver, hook = await _ready(registry, store, clock)
    body = batch(completion_event())
    forged = sign(runtime_hook_value(), body)
    for _ in range(1000):
        result = await _deliver(receiver, hook.handle, body, signature=forged)
        assert (result.status_code, result.outcome) == (401, RequestOutcome.SIGNATURE_MISMATCH)
    assert store.reads <= 1
    valid = await _deliver(receiver, hook.handle, body, signature=sign(hook.hook_value, body))
    assert valid.status_code == 200, "RL-1 at the receiver: the valid one still passes"


@pytest.mark.parametrize(
    "signature",
    [None, "", "A" * 64, "a" * 63, "é" * 32, "a" * 63 + "\n"],
    ids=["missing", "empty", "uppercase", "short", "non-ascii", "newline"],
)
async def test_bad_signature_shapes_are_401_with_no_key_read(
    signature: str | None,
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    clock: FakeClock,
) -> None:
    """R-A1 (D6 TDD fixture or review id)."""
    receiver, hook = await _ready(registry, store, clock)
    body = batch(completion_event())
    raw: list[tuple[bytes, bytes]] = []
    if signature is not None:
        raw.append((b"x-hook-signature", signature.encode("utf-8")))
    result = await receiver.receive(handle=hook.handle, raw_headers=raw, body=body_stream(body))
    assert (result.status_code, result.outcome) == (401, RequestOutcome.SIGNATURE_INVALID)
    assert store.reads == 0


async def test_duplicated_header_garbage_json_and_wrong_key_are_401(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """R-A1 (D6 TDD fixture or review id)."""
    receiver, hook = await _ready(registry, store, clock)
    body = batch(completion_event())
    good = sign(hook.hook_value, body)
    duplicated = await _deliver(
        receiver, hook.handle, body, signature=good, extra=[(b"x-hook-signature", good.encode())]
    )
    assert duplicated.status_code == 401
    garbage = b"{not json"
    wrong = await _deliver(
        receiver, hook.handle, garbage, signature=sign(runtime_hook_value(), garbage)
    )
    assert wrong.status_code == 401
    other = make_active_hook(registry, store, clock)
    a_to_b = await _deliver(receiver, hook.handle, body, signature=sign(other.hook_value, body))
    assert a_to_b.status_code == 401
    # Twin: the correct signature gives 200.
    assert (await _deliver(receiver, hook.handle, body, signature=good)).status_code == 200


async def test_compressed_body_is_415_and_spends_the_budget(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """ENC-1, A N-1 (D6 TDD fixture or review id)."""
    receiver, hook = await _ready(registry, store, clock)
    body = batch(completion_event())
    before = receiver.verifier.budget.remaining(hook.handle, int(clock()))
    result = await _deliver(
        receiver,
        hook.handle,
        body,
        signature=sign(hook.hook_value, body),
        extra=[(b"content-encoding", b"gzip")],
    )
    assert (result.status_code, result.outcome) == (415, RequestOutcome.ENCODING_REFUSED)
    assert receiver.verifier.budget.remaining(hook.handle, int(clock())) == before - 1
    assert store.reads == 0


async def test_oversize_bodies_are_413_before_any_key_read(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """SZ-1 (D6 TDD fixture or review id)."""
    receiver, hook = await _ready(registry, store, clock)
    declared = await _deliver(
        receiver,
        hook.handle,
        b"",
        signature="a" * 64,
        extra=[(b"content-length", str(10 * 1024 * 1024).encode())],
    )
    assert (declared.status_code, declared.outcome) == (413, RequestOutcome.TOO_LARGE)
    mib = b"x" * (1024 * 1024)
    chunked = await _deliver(receiver, hook.handle, b"", signature="a" * 64, chunks=[mib] * 10)
    assert (chunked.status_code, chunked.outcome) == (413, RequestOutcome.TOO_LARGE)
    assert store.reads == 0, "413 comes before any key read or HMAC"
    # Twin: 200 KiB passes.
    padded = json.dumps({"events": [], "pad": "p" * (200 * 1024)}).encode()
    ok = await _deliver(receiver, hook.handle, padded, signature=sign(hook.hook_value, padded))
    assert ok.status_code == 200


async def test_key_read_error_is_500_never_401(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """SM-1, A C-8 (D6 TDD fixture or review id)."""
    receiver, hook = await _ready(registry, store, clock)
    store.fail_read = True
    body = batch(completion_event())
    result = await _deliver(receiver, hook.handle, body, signature=sign(hook.hook_value, body))
    assert (result.status_code, result.outcome) == (500, RequestOutcome.KEY_UNAVAILABLE)


async def test_compromised_hook_is_403_after_a_valid_signature(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """W TM-8, section 4 step 7 (D6 TDD fixture or review id)."""
    receiver, hook = await _ready(registry, store, clock)
    body = batch(completion_event())
    signature = sign(hook.hook_value, body)
    assert (await _deliver(receiver, hook.handle, body, signature=signature)).status_code == 200
    registry.mark_compromised(handle=hook.handle, now=int(clock()))
    other = batch(completion_event())
    result = await _deliver(receiver, hook.handle, other, signature=sign(hook.hook_value, other))
    assert (result.status_code, result.outcome) == (403, RequestOutcome.NOT_ACTIVE)
    assert result.deliveries == ()


async def test_valid_delivery_persists_accepted_rows_and_touches_liveness(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    receiver, hook = await _ready(registry, store, clock)
    events = [completion_event(), completion_event()]
    body = batch(*events)
    result = await _deliver(receiver, hook.handle, body, signature=sign(hook.hook_value, body))
    assert (result.status_code, result.outcome) == (200, RequestOutcome.ACCEPTED)
    assert [d.created for d in result.deliveries] == [True, True]
    for event, delivery in zip(events, result.deliveries):
        row = registry.get_delivery(hook.handle, delivery.event_key)
        assert row is not None and row.state is DeliveryState.ACCEPTED
        assert row.attempts == 0 and row.received_at == int(clock())
        assert row.event_json == canonical_event_json(event)
        assert row.created_at == event["created_at"]
        assert delivery.event_key == event_key(canonical_event_json(event))
    live = registry._client.get_item(
        TableName=registry._table,
        Key={"pk": {"S": f"PROJECT#{hook.project_gid}"}, "sk": {"S": "LIVE"}},
        ConsistentRead=True,
    )["Item"]
    assert live["last_event_at"]["N"] == str(int(clock()))
    assert "last_heartbeat_at" not in live
    assert [u[0] for u in registry.query_undecided()] == [hook.handle, hook.handle]


async def test_heartbeat_touches_liveness_and_persists_nothing(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    receiver, hook = await _ready(registry, store, clock)
    body = batch()
    result = await _deliver(receiver, hook.handle, body, signature=sign(hook.hook_value, body))
    assert (result.status_code, result.outcome, result.deliveries) == (
        200,
        RequestOutcome.HEARTBEAT,
        (),
    )
    live = registry._client.get_item(
        TableName=registry._table,
        Key={"pk": {"S": f"PROJECT#{hook.project_gid}"}, "sk": {"S": "LIVE"}},
        ConsistentRead=True,
    )["Item"]
    assert live["last_heartbeat_at"]["N"] == str(int(clock()))
    assert registry.query_undecided() == []


@pytest.mark.parametrize("body", [b"[]", b'{"events": {}}', b'{"events": [1]}', b"{nope"])
async def test_verified_but_malformed_body_is_400(
    body: bytes, registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    receiver, hook = await _ready(registry, store, clock)
    result = await _deliver(receiver, hook.handle, body, signature=sign(hook.hook_value, body))
    assert (result.status_code, result.outcome) == (400, RequestOutcome.BODY_INVALID)


async def test_persist_error_is_500_never_noop(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """R-A6 (D6 TDD fixture or review id)."""
    receiver, hook = await _ready(registry, store, clock)

    def refuse(**kwargs: Any) -> bool:
        raise HookRegistryUnavailable("simulated", error_code="InternalServerError")

    registry.put_delivery = refuse  # type: ignore[method-assign]
    body = batch(completion_event())
    result = await _deliver(receiver, hook.handle, body, signature=sign(hook.hook_value, body))
    assert (result.status_code, result.outcome) == (500, RequestOutcome.PERSIST_FAILED)


async def test_redelivery_never_resets_state_or_first_receipt(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """A N4-2: the delivery put is conditional; a redelivery keeps the first-receipt time."""
    receiver, hook = await _ready(registry, store, clock)
    body = batch(completion_event())
    first = await _deliver(receiver, hook.handle, body, signature=sign(hook.hook_value, body))
    (delivery,) = first.deliveries
    first_receipt = int(clock())
    claimed = registry.claim_delivery(
        handle=hook.handle, event_key=delivery.event_key, owner="o1", now=first_receipt
    )
    assert claimed is not None and claimed.state is DeliveryState.CLAIMED
    clock.now += 600
    again = await _deliver(receiver, hook.handle, body, signature=sign(hook.hook_value, body))
    assert [d.created for d in again.deliveries] == [False]
    row = registry.get_delivery(hook.handle, delivery.event_key)
    assert row is not None
    assert (row.state, row.received_at, row.attempts, row.claim_owner) == (
        DeliveryState.CLAIMED,
        first_receipt,
        1,
        "o1",
    )


# ---------------------------------------------------------------------------
# DUP-1, DUP-2a, DUP-2b: the receiver half (the A4 keys make "one decision")
# ---------------------------------------------------------------------------


async def test_same_event_through_two_webhooks_reaches_the_decider_once_per_webhook(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """DUP-1 and DUP-2a, the receiver half (D6 TDD fixture or review id)."""
    decider = RecordingDecider()
    a = make_active_hook(registry, store, clock)
    b = make_active_hook(registry, store, clock)
    receiver = _receiver(
        registry, store, clock, decider=decider, project_gids=[a.project_gid, b.project_gid]
    )
    assert await receiver.refresh_index() == 2
    event = completion_event()
    body = batch(event)
    for hook in (a, b):
        result = await _deliver(receiver, hook.handle, body, signature=sign(hook.hook_value, body))
        await receiver.decide_after_response(result.deliveries)
    assert len(decider.calls) == 2
    first, second = decider.calls
    assert first.event_key == second.event_key, "one event, one content key"
    assert dict(first.event) == dict(second.event) == event
    assert {first.handle, second.handle} == {a.handle, b.handle}
    # Redelivering either again never reaches the decider a second time for that row.
    again = await _deliver(receiver, a.handle, body, signature=sign(a.hook_value, body))
    await receiver.decide_after_response(again.deliveries)
    assert len(decider.calls) == 2


async def test_complete_reopen_complete_are_three_rows_never_merged(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """DUP-2b, the receiver half (D6 TDD fixture or review id)."""
    decider = RecordingDecider()
    receiver, hook = await _ready(registry, store, clock, decider=decider)
    task, user = runtime_gid(), runtime_gid()
    events = [
        completion_event(task_gid=task, user_gid=user, created_at=f"2026-11-13T19:0{i}:00.000Z")
        for i in range(3)
    ]
    events[1]["change"] = {"field": "completed", "action": "changed", "new_value": False}
    body = batch(*events)
    result = await _deliver(receiver, hook.handle, body, signature=sign(hook.hook_value, body))
    assert len({d.event_key for d in result.deliveries}) == 3
    await receiver.decide_after_response(result.deliveries)
    assert [c.created_at for c in decider.calls] == [e["created_at"] for e in events]


# ---------------------------------------------------------------------------
# After the response: claim, decide, close (section 5 step 1; W F-11)
# ---------------------------------------------------------------------------


async def test_decided_rows_leave_the_undecided_index(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    decider = RecordingDecider()
    receiver, hook = await _ready(registry, store, clock, decider=decider)
    body = batch(completion_event())
    result = await _deliver(receiver, hook.handle, body, signature=sign(hook.hook_value, body))
    await receiver.decide_after_response(result.deliveries)
    (delivery,) = result.deliveries
    row = registry.get_delivery(hook.handle, delivery.event_key)
    assert row is not None and row.state is DeliveryState.DECIDED and row.attempts == 1
    assert registry.query_undecided() == []
    assert decider.calls[0].claim_owner == row.claim_owner


@pytest.mark.parametrize("mode", ["deferred", "failed"])
async def test_deferred_or_failed_decide_leaves_the_row_claimed_for_the_sweeper(
    mode: str, registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    decider = (
        RecordingDecider(DecideOutcome.DEFERRED)
        if mode == "deferred"
        else RecordingDecider(fail=True)
    )
    receiver, hook = await _ready(registry, store, clock, decider=decider)
    body = batch(completion_event())
    result = await _deliver(receiver, hook.handle, body, signature=sign(hook.hook_value, body))
    await receiver.decide_after_response(result.deliveries)  # never raises
    (delivery,) = result.deliveries
    row = registry.get_delivery(hook.handle, delivery.event_key)
    assert row is not None and row.state is DeliveryState.CLAIMED
    assert len(registry.query_undecided()) == 1


async def test_redelivery_never_takes_a_live_or_stale_claim(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """SW-2b, the receiver half: Only the sweeper takes a stale claim (A C-7); a redelivery defers."""
    decider = RecordingDecider()
    receiver, hook = await _ready(registry, store, clock, decider=decider)
    body = batch(completion_event())
    first = await _deliver(receiver, hook.handle, body, signature=sign(hook.hook_value, body))
    (delivery,) = first.deliveries
    # The first task claims, then crashes before deciding.
    assert registry.claim_delivery(
        handle=hook.handle, event_key=delivery.event_key, owner="dead-task", now=int(clock())
    )
    for advance in (10, 600):  # inside the lease, then long past it
        clock.now += advance
        again = await _deliver(receiver, hook.handle, body, signature=sign(hook.hook_value, body))
        await receiver.decide_after_response(again.deliveries)
    assert decider.calls == []
    row = registry.get_delivery(hook.handle, delivery.event_key)
    assert row is not None and (row.state, row.claim_owner) == (DeliveryState.CLAIMED, "dead-task")


# ---------------------------------------------------------------------------
# The index snapshot
# ---------------------------------------------------------------------------


async def test_index_follows_the_active_rows_and_keeps_the_last_snapshot_on_failure(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    receiver, hook = await _ready(registry, store, clock)
    assert receiver.knows(hook.handle)

    def broken(*args: Any, **kwargs: Any) -> Any:
        raise HookRegistryUnavailable("simulated")

    registry.get_active_handle = broken  # type: ignore[method-assign]
    with pytest.raises(HookRegistryUnavailable):
        await receiver.refresh_index()
    assert receiver.knows(hook.handle), "a failed refresh never empties the snapshot"


async def test_an_unloaded_snapshot_refuses_everything(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    hook = make_active_hook(registry, store, clock)
    receiver = _receiver(registry, store, clock, project_gids=[hook.project_gid])
    body = batch(completion_event())
    result = await _deliver(receiver, hook.handle, body, signature=sign(hook.hook_value, body))
    assert result.status_code == 404, "fail closed until the first load"


# ---------------------------------------------------------------------------
# The builder (W F-4, R-A6) and real clients only on `production` (auth-bench A3-2)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("flag", OFF_VALUES)
def test_builder_with_flag_off_returns_none_and_calls_no_factory(flag: str | None) -> None:
    def factory() -> Any:
        raise AssertionError("factory called with the shadow flag off")

    env = _env(flag)
    env["ASANA_HOOK_ENVIRONMENT"] = "production"
    assert (
        build_shadow_receiver(
            environ=env,
            registry_factory=factory,
            store_factory=factory,
            decider_factory=factory,
            projects_factory=factory,
        )
        is None
    )


def test_builder_with_flag_on_and_refused_marker_fails_startup_before_factories() -> None:
    with pytest.raises(HookEnvironmentRefused):
        build_shadow_receiver(
            environ={"ASANA_HOOK_SHADOW_ENABLED": "1"},
            registry_factory=lambda: pytest.fail("factory called"),
            store_factory=lambda: pytest.fail("factory called"),
            decider_factory=lambda: pytest.fail("factory called"),
            projects_factory=lambda: pytest.fail("factory called"),
        )


def test_registry_construction_failure_fails_startup_never_noop() -> None:
    """W F-4, R-A6 (D6 TDD fixture or review id)."""

    def no_table() -> Any:
        return HookRegistry.from_env(environ={"ASANA_HOOK_ENVIRONMENT": "test"})

    with pytest.raises(HookRegistryUnavailable):
        build_shadow_receiver(
            environ=dict(SHADOW_TEST_ENV),
            registry_factory=no_table,
            store_factory=lambda: pytest.fail("store built after a registry failure"),
            decider_factory=RecordingDecider,
            projects_factory=lambda: (),
        )


def test_builder_with_flag_on_and_test_adapters_builds(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """W F-4 twin (D6 TDD fixture or review id)."""
    receiver = build_shadow_receiver(
        environ=dict(SHADOW_TEST_ENV),
        registry_factory=lambda: registry,
        store_factory=lambda: store,
        decider_factory=RecordingDecider,
        projects_factory=lambda: (),
        clock=clock,
    )
    assert isinstance(receiver, ShadowReceiver)


class _Boto3Recorder:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def client(self, service: str, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(service)
        return SimpleNamespace(service=service)


REFUSED_MARKERS = [
    {},
    {"ASANA_HOOK_ENVIRONMENT": ""},
    {"ASANA_HOOK_ENVIRONMENT": "test"},
    {"ASANA_HOOK_ENVIRONMENT": "local"},
    {"ASANA_HOOK_ENVIRONMENT": "staging"},
    {"ASANA_HOOK_ENVIRONMENT": "prod"},
    {"ASANA_HOOK_ENVIRONMENT": "Production"},
    {"ASANA_HOOK_ENVIRONMENT": " production"},
    {"ASANA_HOOK_ENVIRONMENT": "production\n"},
]


@pytest.mark.parametrize("marker", REFUSED_MARKERS)
def test_real_dynamodb_client_is_built_only_on_production(
    marker: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """auth-bench A3-2 (D6 TDD fixture or review id)."""
    recorder = _Boto3Recorder()
    monkeypatch.setitem(sys.modules, "boto3", recorder)
    with pytest.raises(HookEnvironmentRefused):
        HookRegistry(table_name="t", environ=marker)
    with pytest.raises(HookEnvironmentRefused):
        HookRegistry.from_env(environ={**marker, "ASANA_HOOK_REGISTRY_TABLE": "t"})
    assert recorder.calls == []


def test_production_marker_builds_the_real_dynamodb_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """auth-bench A3-2 twin (D6 TDD fixture or review id)."""
    recorder = _Boto3Recorder()
    monkeypatch.setitem(sys.modules, "boto3", recorder)
    HookRegistry(table_name="t", environ={"ASANA_HOOK_ENVIRONMENT": "production"})
    assert recorder.calls == ["dynamodb"]


@pytest.mark.parametrize("marker", ["test", "local"])
def test_shadow_on_with_test_marker_refuses_real_factories(
    marker: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """auth-bench A3-2: The flag on and a test marker: real factories refuse, so startup fails, no AWS."""
    recorder = _Boto3Recorder()
    monkeypatch.setitem(sys.modules, "boto3", recorder)
    env = {
        "ASANA_HOOK_SHADOW_ENABLED": "1",
        "ASANA_HOOK_ENVIRONMENT": marker,
        "ASANA_HOOK_REGISTRY_TABLE": "t",
    }
    with pytest.raises(HookEnvironmentRefused):
        build_shadow_receiver(
            environ=env,
            registry_factory=lambda: HookRegistry.from_env(environ=env),
            store_factory=lambda: HookStore(environ=env),
            decider_factory=RecordingDecider,
            projects_factory=lambda: (),
        )
    assert recorder.calls == []
    # The real store built under a test marker refuses its read before any client exists.
    store = HookStore(environ=env)
    with pytest.raises(HookStoreRefused):
        store.read_hook_value(handle=secrets.token_hex(16))
    assert store._client is None


class _ReadClient:
    def __init__(self, value: str | None) -> None:
        self.value = value
        self.calls: list[dict[str, Any]] = []

    def get_secret_value(self, **kwargs: Any) -> dict[str, Any]:  # boto3 method name
        self.calls.append(kwargs)
        if self.value is None:
            raise RuntimeError("simulated")
        return {"SecretString": json.dumps({"hook_value": self.value})}


_TASK_ROLE_ENV = {"ASANA_HOOK_ENVIRONMENT": "production", **TASK_ROLE_ENV}


def test_store_read_on_production_with_task_role_reads_the_value() -> None:
    """A C-8 twin (D6 TDD fixture or review id)."""
    value = runtime_hook_value()
    client = _ReadClient(value)
    store = HookStore(client=client, environ=dict(_TASK_ROLE_ENV))
    handle = secrets.token_hex(16)
    assert store.read_hook_value(handle=handle) == value
    assert client.calls == [{"SecretId": f"autom8y/asana/webhook-hook/{handle}"}]


def test_store_read_failure_is_typed_and_carries_no_value() -> None:
    client = _ReadClient(None)
    store = HookStore(client=client, environ=dict(_TASK_ROLE_ENV))
    with pytest.raises(hook_store_module.HookStoreReadFailed) as exc_info:
        store.read_hook_value(handle=secrets.token_hex(16))
    assert "simulated" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# auth-bench A3-1: the handle is never logged, at any level
# ---------------------------------------------------------------------------


async def test_handle_never_appears_in_any_log_line(
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    clock: FakeClock,
    hex_handle: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """auth-bench A3-1 (D6 TDD fixture or review id)."""
    spy = LogSpy()
    for module in (
        receiver_module,
        registration_module,
        liveness_module,
        hook_store_module,
        hook_registry_module,
    ):
        monkeypatch.setattr(module, "logger", spy)
    decider = RecordingDecider(fail=True)
    receiver, hook = await _ready(registry, store, clock, decider=decider)
    registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=int(clock()))
    value = runtime_hook_value()
    await receiver.handshake(handle=hex_handle, hook_header=value)
    await receiver.handshake(handle=hex_handle, hook_header=runtime_hook_value())  # compromise
    body = batch(completion_event())
    signature = sign(hook.hook_value, body)
    ok = await _deliver(receiver, hook.handle, body, signature=signature)
    await receiver.decide_after_response(ok.deliveries)  # decide fails: error-level lines
    await _deliver(receiver, hook.handle, body, signature="b" * 64)
    await _deliver(receiver, hook.handle, body, signature=None)
    await _deliver(receiver, hook.handle, body, extra=[(b"content-encoding", b"gzip")])
    assert len(spy.events) > 8, "positive control: the paths logged"
    rendered = repr(spy.events)
    for handle in (hook.handle, hex_handle):
        assert handle not in rendered
    assert hook_store_module.handle_fingerprint(hook.handle) in rendered, "the fingerprint is"
    for text in (value, hook.hook_value, signature):
        assert text not in rendered
    levels = {level for level, _, _ in spy.events}
    assert {"info", "warning", "error"} <= levels, levels
