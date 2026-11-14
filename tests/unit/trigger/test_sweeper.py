"""D6 sweeper (A3): SW-1, SW-2, SW-2b, the reconciler lease (TDD r4.10 s2a, s5, s9).

Review rows: W F-11 (residual: the claim step and the backstop) and S TM-12 lease (the
sweeper runs under the reconciler lease and reads the sparse ``undecided`` index).

DynamoDB is moto through the real ``HookRegistry``, including the ``undecided`` GSI as
Terraform declares it. The decider is a recorder; the A4 engine is not in this PR, so
"the record is emitted once" in SW-2 is proved here as "the delivery is re-driven to
the decider exactly once, with the same row identity the A4 keys use as their owner".
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

import pytest

from autom8_asana.trigger import liveness as liveness_module
from autom8_asana.trigger.hook_registry import DeliveryState
from autom8_asana.trigger.liveness import DeliveryResult
from autom8_asana.trigger.receiver import (
    ABANDONED_OUTCOME,
    DecideOutcome,
    ShadowReceiver,
    ShadowReceiverDisabled,
)
from autom8_asana.trigger.sweeper import (
    ACCEPTED_GRACE_S,
    CLAIM_LEASE_S,
    MAX_ATTEMPTS,
    SWEEP_INTERVAL_S,
    Sweeper,
)
from tests.unit.trigger.conftest import (
    SHADOW_TEST_ENV,
    FakeClock,
    RecordingDecider,
    batch,
    body_stream,
    completion_event,
    make_active_hook,
    sign,
)

if TYPE_CHECKING:
    from tests.unit.trigger.adapters import InMemoryHookRegistry, InMemoryKeyHookStore

OWNER = "reconciler-owner"


def _sweeper(registry: Any, decider: Any, clock: FakeClock, **kw: Any) -> Sweeper:
    return Sweeper(
        registry=registry,
        decider=decider,
        lease_owner=kw.pop("lease_owner", OWNER),
        clock=clock,
        environ=kw.pop("environ", dict(SHADOW_TEST_ENV)),
        **kw,
    )


async def _persist(
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    clock: FakeClock,
    decider: Any,
    n: int = 1,
) -> tuple[ShadowReceiver, list[Any], str]:
    """Persist ``n`` deliveries and do NOT run the post-response decide (a crash after 200)."""
    hook = make_active_hook(registry, store, clock)
    receiver = ShadowReceiver(
        registry=registry,
        store=store,
        decider=decider,
        project_gids=[hook.project_gid],
        clock=clock,
        environ=dict(SHADOW_TEST_ENV),
    )
    await receiver.refresh_index()
    body = batch(*(completion_event() for _ in range(n)))
    result = await receiver.receive(
        handle=hook.handle,
        raw_headers=[(b"x-hook-signature", sign(hook.hook_value, body).encode())],
        body=body_stream(body),
    )
    assert result.status_code == 200
    return receiver, list(result.deliveries), hook.handle


@pytest.mark.parametrize("flag", [None, "0", "true", "1 ", "1\n"])
def test_sweeper_refuses_to_construct_unless_flag_is_exactly_one(
    flag: str | None, registry: InMemoryHookRegistry, clock: FakeClock
) -> None:
    env = {"ASANA_HOOK_ENVIRONMENT": "test"}
    if flag is not None:
        env["ASANA_HOOK_SHADOW_ENABLED"] = flag
    with pytest.raises(ShadowReceiverDisabled):
        _sweeper(registry, RecordingDecider(), clock, environ=env)


async def test_delivery_killed_after_the_200_is_decided_within_two_minutes(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """SW-1: the post-response decide never ran; the sweeper decides it within 2 minutes."""
    decider = RecordingDecider()
    _, (delivery,), handle = await _persist(registry, store, clock, decider)
    sweeper = _sweeper(registry, decider, clock)
    received = int(clock())
    # Sweeps run every SWEEP_INTERVAL_S; walk them until the row is decided.
    while decider.calls == []:
        clock.now += SWEEP_INTERVAL_S
        await sweeper.run_once()
        assert int(clock()) - received <= 120, "not decided within two minutes"
    assert ACCEPTED_GRACE_S + SWEEP_INTERVAL_S <= 120
    row = registry.get_delivery(handle, delivery.event_key)
    assert row is not None and row.state is DeliveryState.DECIDED
    assert len(decider.calls) == 1
    assert registry.query_undecided() == []


async def test_sweeper_leaves_a_fresh_row_alone_inside_the_grace(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """SW-1 twin (D6 TDD fixture or review id)."""
    decider = RecordingDecider()
    await _persist(registry, store, clock, decider)
    report = await _sweeper(registry, decider, clock).run_once()
    assert report.ran and report.results == [] and decider.calls == []


async def test_delivery_is_abandoned_after_five_failed_attempts(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """SW-1 (D6 TDD fixture or review id)."""
    decider = RecordingDecider(fail=True)
    _, (delivery,), handle = await _persist(registry, store, clock, decider)
    sweeper = _sweeper(registry, decider, clock)
    clock.now += ACCEPTED_GRACE_S
    results: list[DeliveryResult] = []
    for _ in range(MAX_ATTEMPTS):
        report = await sweeper.run_once()
        results += report.results
        clock.now += CLAIM_LEASE_S  # each failed claim goes stale after the lease
    assert results == [DeliveryResult.DECIDE_FAILED] * (MAX_ATTEMPTS - 1) + [
        DeliveryResult.ABANDONED
    ]
    assert len(decider.calls) == MAX_ATTEMPTS
    row = registry.get_delivery(handle, delivery.event_key)
    assert row is not None and row.state is DeliveryState.DECIDED
    assert (row.attempts, row.outcome) == (MAX_ATTEMPTS, ABANDONED_OUTCOME)
    assert registry.query_undecided() == []
    report = await sweeper.run_once()
    assert report.results == [] and len(decider.calls) == MAX_ATTEMPTS, "never re-driven"


async def test_stale_claim_is_re_driven_once_with_the_same_row_identity(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """SW-2: killed between the key and the record; the row stays claimed until stale."""
    decider = RecordingDecider()
    _, (delivery,), handle = await _persist(registry, store, clock, decider)
    claimed = registry.claim_delivery(
        handle=handle, event_key=delivery.event_key, owner="dead-task", now=int(clock())
    )
    assert claimed is not None
    sweeper = _sweeper(registry, decider, clock)
    clock.now += CLAIM_LEASE_S - 1
    report = await sweeper.run_once()
    assert report.results == [DeliveryResult.CLAIM_LOST], "a live claim is left alone"
    assert decider.calls == []
    clock.now += 2
    report = await sweeper.run_once()
    assert report.results == [DeliveryResult.DECIDED]
    (call,) = decider.calls
    assert (call.handle, call.event_key) == (handle, delivery.event_key)
    assert call.attempts == 2 and call.claim_owner != "dead-task"
    await sweeper.run_once()
    assert len(decider.calls) == 1, "decided rows are never re-driven"


async def test_two_sweepers_racing_on_one_stale_claim_take_it_once(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """SW-2 (D6 TDD fixture or review id)."""
    decider = RecordingDecider()
    _, (delivery,), handle = await _persist(registry, store, clock, decider)
    registry.claim_delivery(
        handle=handle, event_key=delivery.event_key, owner="dead-task", now=int(clock())
    )
    clock.now += CLAIM_LEASE_S + 1
    stale = int(clock()) - CLAIM_LEASE_S
    winners = [
        registry.claim_delivery(
            handle=handle,
            event_key=delivery.event_key,
            owner=o,
            now=int(clock()),
            stale_before=stale,
        )
        for o in ("sweeper-a", "sweeper-b")
    ]
    assert [w is not None for w in winners] == [True, False]


async def test_crash_after_claim_then_redelivery_inside_the_lease_is_one_decision(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """SW-2b (A C-7): the redelivery defers; the sweeper takes the stale claim; one decision."""
    decider = RecordingDecider()
    receiver, (delivery,), handle = await _persist(registry, store, clock, decider)
    row = registry.get_delivery(handle, delivery.event_key)
    assert row is not None
    registry.claim_delivery(
        handle=handle, event_key=delivery.event_key, owner="crashed-task", now=int(clock())
    )
    clock.now += 30  # the redelivery lands inside the 2-minute lease
    event = json.loads(row.event_json)
    body = batch(event)
    hook_value = store.values[f"autom8y/asana/webhook-hook/{handle}"]
    redelivered = await receiver.receive(
        handle=handle,
        raw_headers=[(b"x-hook-signature", sign(hook_value, body).encode())],
        body=body_stream(body),
    )
    assert redelivered.status_code == 200 and [d.created for d in redelivered.deliveries] == [False]
    await receiver.decide_after_response(redelivered.deliveries)
    assert decider.calls == [], "the redelivery defers"
    sweeper = _sweeper(registry, decider, clock)
    for _ in range(4):
        clock.now += SWEEP_INTERVAL_S
        await sweeper.run_once()
    assert len(decider.calls) == 1
    final = registry.get_delivery(handle, delivery.event_key)
    assert final is not None and final.state is DeliveryState.DECIDED


async def test_deferred_decide_is_retried_and_then_decided(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    decider = RecordingDecider(DecideOutcome.DEFERRED)
    _, (delivery,), handle = await _persist(registry, store, clock, decider)
    sweeper = _sweeper(registry, decider, clock)
    clock.now += ACCEPTED_GRACE_S
    assert (await sweeper.run_once()).results == [DeliveryResult.DEFERRED]
    decider.outcome = DecideOutcome.DECIDED
    clock.now += CLAIM_LEASE_S
    assert (await sweeper.run_once()).results == [DeliveryResult.DECIDED]
    row = registry.get_delivery(handle, delivery.event_key)
    assert row is not None and row.state is DeliveryState.DECIDED


# ---------------------------------------------------------------------------
# S TM-12: under the reconciler lease
# ---------------------------------------------------------------------------


async def test_sweeper_skips_while_another_owner_holds_the_lease(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """S TM-12 lease (D6 TDD fixture or review id)."""
    decider = RecordingDecider()
    await _persist(registry, store, clock, decider)
    assert registry.acquire_lease(owner="other-task", now=int(clock()), duration_s=360)
    clock.now += ACCEPTED_GRACE_S
    report = await _sweeper(registry, decider, clock).run_once()
    assert (report.ran, report.skipped_reason) == (False, "lease_held")
    assert decider.calls == []


async def test_sweeper_runs_under_the_reconcilers_own_lease_owner(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """S TM-12 lease twin (D6 TDD fixture or review id)."""
    decider = RecordingDecider()
    await _persist(registry, store, clock, decider)
    assert registry.acquire_lease(owner=OWNER, now=int(clock()), duration_s=360)
    clock.now += ACCEPTED_GRACE_S
    report = await _sweeper(registry, decider, clock, lease_owner=OWNER).run_once()
    assert report.ran and report.results == [DeliveryResult.DECIDED]


async def test_sweeper_reads_the_index_not_a_scan(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    decider = RecordingDecider()
    await _persist(registry, store, clock, decider)
    operations: list[str] = []
    real = registry._client

    class Spy:
        def __getattr__(self, name: str) -> Any:
            operations.append(name)
            return getattr(real, name)

    registry._client = Spy()
    clock.now += ACCEPTED_GRACE_S
    await _sweeper(registry, decider, clock).run_once()
    assert "query" in operations and "scan" not in operations


async def test_undecided_age_gauge_is_set_each_run(
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    clock: FakeClock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[int] = []
    monkeypatch.setattr(
        liveness_module.HOOK_UNDECIDED_OLDEST_SECONDS, "set", lambda v: seen.append(int(v))
    )
    decider = RecordingDecider(fail=True)
    await _persist(registry, store, clock, decider)
    clock.now += 45
    report = await _sweeper(registry, decider, clock).run_once()
    assert report.oldest_undecided_s == 45 and seen[-1] == 45


async def test_run_forever_releases_the_lease_on_an_unexpected_exception(
    registry: InMemoryHookRegistry, clock: FakeClock
) -> None:
    sweeper = _sweeper(registry, RecordingDecider(), clock)

    async def explode() -> Any:
        assert registry.acquire_lease(owner=OWNER, now=int(clock()), duration_s=360)
        raise RuntimeError("unexpected")

    sweeper.run_once = explode  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        await sweeper.run_forever(asyncio.Event())
    assert registry.acquire_lease(owner="next-task", now=int(clock()), duration_s=360)
