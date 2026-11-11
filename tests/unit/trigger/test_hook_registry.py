"""D-1 registry: every transition conditional (TDD r4.6 section 2a; W F-6b, W F-8, A C-6).

Run against moto's DynamoDB through the real conditional expressions. Each refusal has a
passing twin.
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING, Any

import pytest
from botocore.exceptions import ClientError

from autom8_asana.trigger.hook_registry import (
    PENDING_TTL_GRACE_S,
    PENDING_WINDOW_S,
    TABLE_ENV_VAR,
    HookRegistry,
    HookRegistryConflict,
    HookRegistryUnavailable,
    HookState,
)
from tests.unit.trigger.conftest import FakeClock, runtime_gid

if TYPE_CHECKING:
    from tests.unit.trigger.adapters import InMemoryHookRegistry


def _raw_hook(registry: InMemoryHookRegistry, handle: str) -> dict[str, Any]:
    item: dict[str, Any] = registry._client.get_item(
        TableName=registry._table,
        Key={"pk": {"S": f"HOOK#{handle}"}, "sk": {"S": "META"}},
        ConsistentRead=True,
    )["Item"]
    return item


def _handshaken(registry: InMemoryHookRegistry, clock: FakeClock) -> tuple[str, str]:
    handle, project = secrets.token_hex(16), runtime_gid()
    registry.put_pending(handle=handle, resource_gid=project, now=int(clock()))
    registry.mark_handshaken(handle=handle, now=int(clock()))
    return handle, project


def test_put_pending_writes_expiry_and_ttl(
    registry: InMemoryHookRegistry, clock: FakeClock, hex_handle: str
) -> None:
    now = int(clock())
    record = registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=now)
    assert record.expires_at == now + PENDING_WINDOW_S == now + 60
    item = _raw_hook(registry, hex_handle)
    assert item["state"]["S"] == "pending"
    assert int(item["ttl"]["N"]) == now + 60 + PENDING_TTL_GRACE_S


def test_put_pending_never_overwrites(
    registry: InMemoryHookRegistry, clock: FakeClock, hex_handle: str
) -> None:
    registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=int(clock()))
    registry.mark_handshaken(handle=hex_handle, now=int(clock()))
    with pytest.raises(HookRegistryConflict):
        registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=int(clock()))
    record = registry.get_hook(hex_handle)
    assert record is not None and record.state is HookState.HANDSHAKEN


def test_handshaken_requires_pending(registry: InMemoryHookRegistry, clock: FakeClock) -> None:
    handle, _ = _handshaken(registry, clock)
    with pytest.raises(HookRegistryConflict):
        registry.mark_handshaken(handle=handle, now=int(clock()))


def test_handshaken_requires_unexpired(
    registry: InMemoryHookRegistry, clock: FakeClock, hex_handle: str
) -> None:
    registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=int(clock()))
    with pytest.raises(HookRegistryConflict):
        registry.mark_handshaken(handle=hex_handle, now=int(clock()) + PENDING_WINDOW_S)
    registry.mark_handshaken(handle=hex_handle, now=int(clock()) + PENDING_WINDOW_S - 1)


def test_handshaken_on_missing_row_conflicts(
    registry: InMemoryHookRegistry, clock: FakeClock, hex_handle: str
) -> None:
    with pytest.raises(HookRegistryConflict):
        registry.mark_handshaken(handle=hex_handle, now=int(clock()))
    assert registry.get_hook(hex_handle) is None, "a conditional update never creates a row"


def test_activate_requires_handshaken(
    registry: InMemoryHookRegistry, clock: FakeClock, hex_handle: str
) -> None:
    project = runtime_gid()
    registry.put_pending(handle=hex_handle, resource_gid=project, now=int(clock()))
    with pytest.raises(HookRegistryConflict):
        registry.activate(
            handle=hex_handle,
            project_gid=project,
            webhook_gid="w",
            now=int(clock()),
            from_state=HookState.HANDSHAKEN,
            previous_handle=None,
        )
    assert registry.get_active_handle(project) is None, "the transaction wrote nothing"


def test_activate_twin_sets_active_and_drops_ttl(
    registry: InMemoryHookRegistry, clock: FakeClock
) -> None:
    handle, project = _handshaken(registry, clock)
    registry.activate(
        handle=handle,
        project_gid=project,
        webhook_gid="w",
        now=int(clock()),
        from_state=HookState.HANDSHAKEN,
        previous_handle=None,
    )
    record = registry.get_hook(handle)
    assert record is not None and record.state is HookState.ACTIVE and record.webhook_gid == "w"
    assert "ttl" not in _raw_hook(registry, handle)
    assert registry.get_active_handle(project) == handle


def test_one_active_per_project(registry: InMemoryHookRegistry, clock: FakeClock) -> None:
    first, project = _handshaken(registry, clock)
    registry.activate(
        handle=first,
        project_gid=project,
        webhook_gid="w1",
        now=int(clock()),
        from_state=HookState.HANDSHAKEN,
        previous_handle=None,
    )
    second = secrets.token_hex(16)
    registry.put_pending(handle=second, resource_gid=project, now=int(clock()))
    registry.mark_handshaken(handle=second, now=int(clock()))
    with pytest.raises(HookRegistryConflict):
        registry.activate(
            handle=second,
            project_gid=project,
            webhook_gid="w2",
            now=int(clock()),
            from_state=HookState.HANDSHAKEN,
            previous_handle=None,
        )
    with pytest.raises(HookRegistryConflict):
        registry.activate(
            handle=second,
            project_gid=project,
            webhook_gid="w2",
            now=int(clock()),
            from_state=HookState.HANDSHAKEN,
            previous_handle=secrets.token_hex(16),
        )
    assert registry.get_active_handle(project) == first
    record = registry.get_hook(second)
    assert record is not None and record.state is HookState.HANDSHAKEN, "rolled back"
    # Twin: naming the current holder replaces it.
    registry.activate(
        handle=second,
        project_gid=project,
        webhook_gid="w2",
        now=int(clock()),
        from_state=HookState.HANDSHAKEN,
        previous_handle=first,
    )
    assert registry.get_active_handle(project) == second


def test_adopt_from_create_unknown_requires_handshaken_at(
    registry: InMemoryHookRegistry, clock: FakeClock, hex_handle: str
) -> None:
    project = runtime_gid()
    registry.put_pending(handle=hex_handle, resource_gid=project, now=int(clock()))
    registry.mark_create_unknown(handle=hex_handle, now=int(clock()))
    with pytest.raises(HookRegistryConflict):
        registry.activate(
            handle=hex_handle,
            project_gid=project,
            webhook_gid="w",
            now=int(clock()),
            from_state=HookState.CREATE_UNKNOWN,
            previous_handle=None,
        )
    handle, project2 = _handshaken(registry, clock)
    registry.mark_create_unknown(handle=handle, now=int(clock()))
    registry.activate(
        handle=handle,
        project_gid=project2,
        webhook_gid="w",
        now=int(clock()),
        from_state=HookState.CREATE_UNKNOWN,
        previous_handle=None,
    )
    assert registry.get_active_handle(project2) == handle


def test_activate_from_other_states_is_refused(
    registry: InMemoryHookRegistry, clock: FakeClock
) -> None:
    handle, project = _handshaken(registry, clock)
    for state in (HookState.PENDING, HookState.ACTIVE, HookState.FAILED, HookState.REMOVED):
        with pytest.raises(HookRegistryConflict):
            registry.activate(
                handle=handle,
                project_gid=project,
                webhook_gid="w",
                now=int(clock()),
                from_state=state,
                previous_handle=None,
            )


def test_compromised_is_sticky_against_removed(
    registry: InMemoryHookRegistry, clock: FakeClock
) -> None:
    handle, _ = _handshaken(registry, clock)
    registry.mark_compromised(handle=handle, now=int(clock()))
    with pytest.raises(HookRegistryConflict):
        registry.mark_removed(handle=handle, now=int(clock()))
    record = registry.get_hook(handle)
    assert record is not None and record.state is HookState.COMPROMISED
    other, _ = _handshaken(registry, clock)
    registry.mark_removed(handle=other, now=int(clock()))
    record = registry.get_hook(other)
    assert record is not None and record.state is HookState.REMOVED


def test_failed_only_from_open_states(registry: InMemoryHookRegistry, clock: FakeClock) -> None:
    handle, project = _handshaken(registry, clock)
    registry.activate(
        handle=handle,
        project_gid=project,
        webhook_gid="w",
        now=int(clock()),
        from_state=HookState.HANDSHAKEN,
        previous_handle=None,
    )
    with pytest.raises(HookRegistryConflict):
        registry.mark_failed(handle=handle, now=int(clock()))
    other, _ = _handshaken(registry, clock)
    registry.mark_failed(handle=other, now=int(clock()))


def test_lease_is_exclusive_until_expiry(registry: InMemoryHookRegistry, clock: FakeClock) -> None:
    now = int(clock())
    assert registry.acquire_lease(owner="a", now=now, duration_s=300) is True
    assert registry.acquire_lease(owner="b", now=now + 10, duration_s=300) is False
    assert registry.acquire_lease(owner="a", now=now + 10, duration_s=300) is True, "renew"
    assert registry.acquire_lease(owner="b", now=now + 311, duration_s=300) is True, "expired"
    registry.release_lease(owner="a")  # not held: logged, not raised
    assert registry.acquire_lease(owner="a", now=now + 312, duration_s=300) is False


def test_get_reads_are_consistent_by_default(
    registry: InMemoryHookRegistry, hex_handle: str
) -> None:
    seen: list[dict[str, Any]] = []
    real = registry._client.get_item

    def spy(**kwargs: Any) -> Any:
        seen.append(kwargs)
        return real(**kwargs)

    registry._client.get_item = spy
    registry.get_hook(hex_handle)
    registry.get_active_handle(runtime_gid())
    assert [c["ConsistentRead"] for c in seen] == [True, True]


class _Throttled:
    def get_item(self, **_: Any) -> Any:
        raise ClientError({"Error": {"Code": "ProvisionedThroughputExceededException"}}, "GetItem")


def test_non_conditional_errors_are_unavailable_not_absent(hex_handle: str) -> None:
    registry = HookRegistry(table_name="t", client=_Throttled())
    with pytest.raises(HookRegistryUnavailable) as caught:
        registry.get_hook(hex_handle)
    assert caught.value.error_code == "ProvisionedThroughputExceededException"


def test_from_env_refuses_missing_table_name() -> None:
    with pytest.raises(HookRegistryUnavailable):
        HookRegistry.from_env(environ={}, client=_Throttled())
    with pytest.raises(HookRegistryUnavailable):
        HookRegistry.from_env(environ={TABLE_ENV_VAR: ""}, client=_Throttled())
    assert HookRegistry.from_env(environ={TABLE_ENV_VAR: "t"}, client=_Throttled())._table == "t"


def test_no_scan_anywhere_in_registry() -> None:
    from pathlib import Path

    import autom8_asana.trigger.hook_registry as module

    text = Path(module.__file__).read_text()
    assert '"scan"' not in text and ".scan(" not in text
