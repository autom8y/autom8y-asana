"""D6 registration: HS-1..HS-4, OR-1, R-A5b, warden C-1, auth A2-4 (TDD r4.6 sections 3, 9).

Each fixture has a refusal and a passing twin. Asana is :class:`FakeAsana`, which performs
the handshake during create, as Asana does. DynamoDB is moto, through the real
:class:`HookRegistry` conditional expressions.
"""

from __future__ import annotations

import ast
import secrets
from pathlib import Path
from typing import Any

import pytest

from autom8_asana.client import AsanaClient
from autom8_asana.clients.webhooks import WebhooksClient as SdkWebhooksClient
from autom8_asana.core.types import EntityType
from autom8_asana.errors import AsanaError
from autom8_asana.trigger import registration as registration_module
from autom8_asana.trigger.hook_environment import HookEnvironmentRefused
from autom8_asana.trigger.hook_registry import HookState
from autom8_asana.trigger.ports_webhooks import WebhookCallFailed, WebhooksClient
from autom8_asana.trigger.registration import (
    HandshakeReason,
    Reconciler,
    Registrar,
    RegistrationRefused,
    RegistrationStatus,
    ShadowRegistrationDisabled,
    build_shadow_registration,
    handle_handshake,
)
from autom8_asana.trigger.watched_projects import (
    TRIGGER_FILTERS,
    WATCHED_ENTITY_TYPES,
    TriggerKind,
    watched_projects,
)
from tests.unit.trigger.adapters import InMemoryHookRegistry, InMemoryKeyHookStore
from tests.unit.trigger.conftest import (
    SHADOW_TEST_ENV,
    TARGET_BASE,
    FakeAsana,
    FakeClock,
    project_with,
    runtime_gid,
    runtime_hook_value,
    sdk_client_backed_by,
)

BOTH = (TriggerKind.COMPLETION, TriggerKind.SECTION_MOVE)


def _registrar(port: Any, registry: Any, store: Any, clock: FakeClock, **kw: Any) -> Registrar:
    return Registrar(
        webhooks=port,
        registry=registry,
        store=store,
        workspace_gid=runtime_gid(),
        target_base_url=TARGET_BASE,
        clock=clock,
        environ=kw.pop("environ", SHADOW_TEST_ENV),
        **kw,
    )


# ---------------------------------------------------------------------------
# R-A5b (registration side): construction refuses anything but the narrow port
# ---------------------------------------------------------------------------


def test_full_asana_client_is_refused_at_construction(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock
) -> None:
    """R-A5b (D6 TDD fixture or review id)."""
    full = AsanaClient.__new__(AsanaClient)
    with pytest.raises(RegistrationRefused):
        _registrar(full, registry, store, clock)


def test_sdk_webhooks_client_with_full_crud_is_refused(
    fake_asana: FakeAsana,
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    clock: FakeClock,
) -> None:
    """R-A5b (D6 TDD fixture or review id)."""
    with pytest.raises(RegistrationRefused):
        _registrar(sdk_client_backed_by(fake_asana), registry, store, clock)
    assert fake_asana.calls == []


def test_narrow_webhooks_port_constructs(
    port: WebhooksClient,
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    clock: FakeClock,
) -> None:
    """R-A5b twin (D6 TDD fixture or review id)."""
    assert isinstance(_registrar(port, registry, store, clock), Registrar)


# ---------------------------------------------------------------------------
# Happy path and auth A2-4 (no map row registers nothing)
# ---------------------------------------------------------------------------


async def test_register_mapped_project_goes_active(
    registrar: Registrar,
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    fake_asana: FakeAsana,
) -> None:
    project = project_with(*BOTH)
    outcome = await registrar.register_project(project)
    assert outcome.status is RegistrationStatus.ACTIVE
    record = registry.get_hook(outcome.handle)
    assert record is not None and record.state is HookState.ACTIVE
    assert record.handshaken_at is not None and record.webhook_gid in fake_asana.webhooks
    assert registry.get_active_handle(project.project_gid) == outcome.handle
    assert store.has_value(outcome.handle)
    assert len(outcome.handle) == 32 and int(outcome.handle, 16) >= 0
    (create,) = fake_asana.create_calls()
    assert create["target"] == f"{TARGET_BASE}/{outcome.handle}"
    assert create["filters"] == [dict(TRIGGER_FILTERS[k]) for k in BOTH]


async def test_project_without_a_trigger_map_row_makes_zero_asana_calls(
    registrar: Registrar, fake_asana: FakeAsana, registry: InMemoryHookRegistry
) -> None:
    """auth A2-4 (D6 TDD fixture or review id)."""
    project = project_with()  # no trigger-map row
    outcome = await registrar.register_project(project)
    assert outcome.status is RegistrationStatus.NO_MAP_ROW
    outcomes = await registrar.reconcile_project(project)
    assert [o.status for o in outcomes] == [RegistrationStatus.NO_MAP_ROW]
    assert fake_asana.calls == [], "no create, no list, no get for an unmapped project"
    assert registry.get_active_handle(project.project_gid) is None


@pytest.mark.parametrize("kind", list(TriggerKind))
async def test_one_trigger_kind_registers_only_its_filter(
    kind: TriggerKind, registrar: Registrar, fake_asana: FakeAsana
) -> None:
    """auth A2-4 twin (D6 TDD fixture or review id)."""
    outcome = await registrar.register_project(project_with(kind))
    assert outcome.status is RegistrationStatus.ACTIVE
    (create,) = fake_asana.create_calls()
    assert create["filters"] == [dict(TRIGGER_FILTERS[kind])]


def test_shipped_trigger_map_is_empty_so_nothing_registers() -> None:
    """auth A2-4 (D6 TDD fixture or review id)."""

    class Source:
        def get_primary_gid(self, entity_type: EntityType) -> str:
            return runtime_gid()

    projects = watched_projects(Source())
    assert [p.trigger_kinds for p in projects] == [(), ()]
    twin = watched_projects(Source(), trigger_map={})
    assert all(not p.filters() for p in twin)


def test_section_move_filter_and_completion_filter_shapes() -> None:
    assert TRIGGER_FILTERS[TriggerKind.COMPLETION] == {
        "resource_type": "task",
        "action": "changed",
        "fields": ["completed"],
    }
    assert TRIGGER_FILTERS[TriggerKind.SECTION_MOVE] == {"resource_type": "task", "action": "added"}


# ---------------------------------------------------------------------------
# warden C-1: shadow off makes ZERO Asana calls; the project list is AssetEdit and Offer
# ---------------------------------------------------------------------------


async def test_shadow_off_builds_nothing_and_calls_nothing(fake_asana: FakeAsana) -> None:
    """warden C-1, warden-bench F-6 flag variants (D6 TDD fixture or review id)."""
    built: list[str] = []

    def factory(name: str) -> Any:
        def make() -> Any:
            built.append(name)
            raise AssertionError(f"{name} factory called with shadow off")

        return make

    # warden-bench F-6 on #541: "true", "1 " and "1\n" are not exactly "1".
    for environ in (
        {},
        {"ASANA_HOOK_ENVIRONMENT": "production"},
        {"ASANA_HOOK_SHADOW_ENABLED": "0"},
        {"ASANA_HOOK_SHADOW_ENABLED": "true"},
        {"ASANA_HOOK_SHADOW_ENABLED": "1 "},
        {"ASANA_HOOK_SHADOW_ENABLED": "1\n"},
        {"ASANA_HOOK_SHADOW_ENABLED": "", "ASANA_HOOK_ENVIRONMENT": "test"},
    ):
        result = build_shadow_registration(
            environ=environ,
            webhooks_factory=factory("webhooks"),
            registry_factory=factory("registry"),
            store_factory=factory("store"),
            projects_factory=factory("projects"),
            workspace_gid=runtime_gid(),
            target_base_url=TARGET_BASE,
        )
        assert result is None
    assert built == []
    assert fake_asana.calls == []


def test_shadow_off_refuses_the_registrar_and_the_reconciler(
    port: WebhooksClient,
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    clock: FakeClock,
    registrar: Registrar,
    fake_asana: FakeAsana,
) -> None:
    """warden C-1 (D6 TDD fixture or review id)."""
    with pytest.raises(ShadowRegistrationDisabled):
        _registrar(port, registry, store, clock, environ={"ASANA_HOOK_ENVIRONMENT": "test"})
    with pytest.raises(ShadowRegistrationDisabled):
        Reconciler(registrar=registrar, registry=registry, projects=(), environ={})
    assert fake_asana.calls == []


def test_watched_projects_are_asset_edit_and_offer_only() -> None:
    """warden C-1 (D6 TDD fixture or review id)."""
    assert WATCHED_ENTITY_TYPES == (EntityType.ASSET_EDIT, EntityType.OFFER)
    asked: list[EntityType] = []

    class Source:
        def get_primary_gid(self, entity_type: EntityType) -> str:
            asked.append(entity_type)
            return runtime_gid()

    projects = watched_projects(Source())
    assert [p.entity_type for p in projects] == [EntityType.ASSET_EDIT, EntityType.OFFER]
    assert asked == [EntityType.ASSET_EDIT, EntityType.OFFER]


async def test_shadow_on_builds_and_reconciles(
    port: WebhooksClient,
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    clock: FakeClock,
    fake_asana: FakeAsana,
) -> None:
    """warden C-1 twin (D6 TDD fixture or review id)."""
    project = project_with(TriggerKind.COMPLETION)
    reconciler = build_shadow_registration(
        environ=SHADOW_TEST_ENV,
        webhooks_factory=lambda: port,
        registry_factory=lambda: registry,
        store_factory=lambda: store,
        projects_factory=lambda: (project,),
        workspace_gid=runtime_gid(),
        target_base_url=TARGET_BASE,
        clock=clock,
    )
    assert reconciler is not None
    report = await reconciler.run_once()
    assert report.ran and report.errors == []
    assert [o.status for o in report.outcomes] == [RegistrationStatus.ACTIVE]
    assert len(fake_asana.create_calls()) == 1


def test_shadow_on_with_a_refused_marker_fails_startup() -> None:
    """warden C-1 (D6 TDD fixture or review id)."""
    with pytest.raises(HookEnvironmentRefused):
        build_shadow_registration(
            environ={"ASANA_HOOK_SHADOW_ENABLED": "1"},
            webhooks_factory=lambda: pytest.fail("factory called"),
            registry_factory=lambda: pytest.fail("factory called"),
            store_factory=lambda: pytest.fail("factory called"),
            projects_factory=lambda: pytest.fail("factory called"),
            workspace_gid=runtime_gid(),
            target_base_url=TARGET_BASE,
        )


# ---------------------------------------------------------------------------
# HS-1 .. HS-4: the handshake
# ---------------------------------------------------------------------------


async def _handshake(
    registry: Any, store: Any, clock: FakeClock, handle: str, value: str | None
) -> Any:
    return await handle_handshake(
        handle=handle, hook_header=value, registry=registry, store=store, now=int(clock())
    )


async def test_handshake_for_an_unknown_handle_is_404_without_echo(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock, hex_handle: str
) -> None:
    """HS-1 (D6 TDD fixture or review id)."""
    result = await _handshake(registry, store, clock, hex_handle, runtime_hook_value())
    assert (result.status_code, result.reason, result.echo) == (
        404,
        HandshakeReason.UNKNOWN_HANDLE,
        None,
    )
    malformed = await _handshake(registry, store, clock, "not-a-handle", runtime_hook_value())
    assert malformed.status_code == 404 and malformed.echo is None
    assert store.values == {}


async def test_handshake_for_an_expired_pending_handle_is_403_without_echo(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock, hex_handle: str
) -> None:
    """HS-1 (D6 TDD fixture or review id)."""
    registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=int(clock()))
    clock.now += 61
    result = await _handshake(registry, store, clock, hex_handle, runtime_hook_value())
    assert (result.status_code, result.reason, result.echo) == (403, HandshakeReason.EXPIRED, None)
    assert store.values == {}
    record = registry.get_hook(hex_handle)
    assert record is not None and record.state is HookState.PENDING


async def test_handshake_for_an_active_handle_is_403_without_echo(
    registrar: Registrar,
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    clock: FakeClock,
) -> None:
    """HS-1 (D6 TDD fixture or review id)."""
    outcome = await registrar.register_project(project_with(TriggerKind.COMPLETION))
    result = await _handshake(registry, store, clock, outcome.handle, runtime_hook_value())
    assert result.status_code == 403 and result.echo is None


@pytest.mark.parametrize("header", [None, "", "short", "has a space in it ok", "x" * 257])
async def test_malformed_handshake_header_is_403_and_leaves_the_hook_pending(
    header: str | None,
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    clock: FakeClock,
    hex_handle: str,
) -> None:
    """HS-1 (D6 TDD fixture or review id)."""
    registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=int(clock()))
    result = await _handshake(registry, store, clock, hex_handle, header)
    assert (result.status_code, result.reason, result.echo) == (
        403,
        HandshakeReason.HEADER_INVALID,
        None,
    )
    record = registry.get_hook(hex_handle)
    assert record is not None and record.state is HookState.PENDING


async def test_handshake_for_a_pending_handle_echoes_and_stores_the_value(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock, hex_handle: str
) -> None:
    """HS-1 twin (D6 TDD fixture or review id)."""
    registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=int(clock()))
    value = runtime_hook_value()
    result = await _handshake(registry, store, clock, hex_handle, value)
    assert (result.status_code, result.echo) == (200, value)
    assert value not in repr(result), "the echo never appears in a repr"
    assert store.has_value(hex_handle)
    record = registry.get_hook(hex_handle)
    assert record is not None and record.state is HookState.HANDSHAKEN


async def test_second_handshake_is_403_and_marks_the_hook_compromised(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock, hex_handle: str
) -> None:
    """HS-2 (D6 TDD fixture or review id)."""
    registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=int(clock()))
    first = await _handshake(registry, store, clock, hex_handle, runtime_hook_value())
    second = await _handshake(registry, store, clock, hex_handle, runtime_hook_value())
    assert first.status_code == 200
    assert (second.status_code, second.reason, second.echo) == (
        403,
        HandshakeReason.SECOND_HANDSHAKE,
        None,
    )
    record = registry.get_hook(hex_handle)
    assert record is not None and record.state is HookState.COMPROMISED
    assert [e for e in store.events if e[0] == "store_create"] == [("store_create", hex_handle)]


async def test_a_single_handshake_leaves_the_hook_handshaken(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock, hex_handle: str
) -> None:
    """HS-2 twin (D6 TDD fixture or review id)."""
    registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=int(clock()))
    assert (
        await _handshake(registry, store, clock, hex_handle, runtime_hook_value())
    ).status_code == 200
    record = registry.get_hook(hex_handle)
    assert record is not None and record.state is HookState.HANDSHAKEN


async def test_handshake_that_loses_the_conditional_move_counts_as_the_second(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock, hex_handle: str
) -> None:
    """HS-2: A handshake that read `pending` but lost the conditional move is the second one."""
    registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=int(clock()))
    real_get = registry.get_hook
    reads = {"n": 0}

    def stale_first_read(handle: str, *, consistent: bool = True) -> Any:
        reads["n"] += 1
        if reads["n"] == 1:
            stale = real_get(handle, consistent=consistent)
            registry.mark_handshaken(handle=handle, now=int(clock()))  # the winner lands
            return stale
        return real_get(handle, consistent=consistent)

    registry.get_hook = stale_first_read  # type: ignore[method-assign]
    result = await _handshake(registry, store, clock, hex_handle, runtime_hook_value())
    assert (result.status_code, result.reason) == (403, HandshakeReason.SECOND_HANDSHAKE)
    assert store.values == {}
    record = real_get(hex_handle)
    assert record is not None and record.state is HookState.COMPROMISED


async def test_handshake_reads_the_registry_with_consistent_reads(
    registry: InMemoryHookRegistry, store: InMemoryKeyHookStore, clock: FakeClock, hex_handle: str
) -> None:
    """HS-3 (D6 TDD fixture or review id)."""
    registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=int(clock()))
    seen: list[dict[str, Any]] = []
    real = registry._client.get_item

    def spy(**kwargs: Any) -> Any:
        seen.append(kwargs)
        return real(**kwargs)

    registry._client.get_item = spy
    result = await _handshake(registry, store, clock, hex_handle, runtime_hook_value())
    assert result.status_code == 200
    assert seen and all(call["ConsistentRead"] is True for call in seen)


async def test_handshake_store_failure_is_500_with_no_echo_and_marks_failed(
    registry: InMemoryHookRegistry, clock: FakeClock, hex_handle: str
) -> None:
    """HS-4, A C-2 (D6 TDD fixture or review id)."""
    failing = InMemoryKeyHookStore(environ={"ASANA_HOOK_ENVIRONMENT": "test"}, fail_create=True)
    registry.put_pending(handle=hex_handle, resource_gid=runtime_gid(), now=int(clock()))
    result = await _handshake(registry, failing, clock, hex_handle, runtime_hook_value())
    assert (result.status_code, result.reason, result.echo) == (
        500,
        HandshakeReason.STORE_FAILED,
        None,
    )
    record = registry.get_hook(hex_handle)
    assert record is not None and record.state is HookState.FAILED


async def test_registration_with_a_failing_store_never_goes_active(
    port: WebhooksClient, registry: InMemoryHookRegistry, clock: FakeClock, fake_asana: FakeAsana
) -> None:
    """HS-4 (D6 TDD fixture or review id)."""
    failing = InMemoryKeyHookStore(environ={"ASANA_HOOK_ENVIRONMENT": "test"}, fail_create=True)
    fake_asana.store = failing
    reg = _registrar(port, registry, failing, clock)
    project = project_with(TriggerKind.COMPLETION)
    outcome = await reg.register_project(project)
    assert outcome.status is RegistrationStatus.FAILED
    assert registry.get_active_handle(project.project_gid) is None
    assert fake_asana.webhooks == {}
    record = registry.get_hook(outcome.handle)
    assert record is not None and record.state is HookState.FAILED


# ---------------------------------------------------------------------------
# OR-1: create times out after Asana created the webhook
# ---------------------------------------------------------------------------


async def test_webhook_created_before_a_timeout_is_adopted(
    registrar: Registrar,
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    fake_asana: FakeAsana,
) -> None:
    """OR-1 (D6 TDD fixture or review id)."""
    fake_asana.mode = "timeout_after_create"
    project = project_with(TriggerKind.COMPLETION)
    outcome = await registrar.register_project(project)
    assert outcome.status is RegistrationStatus.ADOPTED
    record = registry.get_hook(outcome.handle)
    assert record is not None and record.state is HookState.ACTIVE
    assert registry.get_active_handle(project.project_gid) == outcome.handle
    assert store.has_value(outcome.handle)


async def test_unadoptable_webhook_is_deleted_with_its_key_last(
    registrar: Registrar,
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    fake_asana: FakeAsana,
    events: list[tuple[str, str]],
) -> None:
    """OR-1 (D6 TDD fixture or review id)."""
    project = project_with(TriggerKind.COMPLETION)
    first = await registrar.register_project(project)  # holds the ACTIVE row
    fake_asana.mode = "timeout_after_create"
    second = await registrar.register_project(project)
    assert second.status is RegistrationStatus.CREATE_UNKNOWN_DELETED
    record = registry.get_hook(second.handle)
    assert record is not None and record.state is HookState.REMOVED
    assert not store.has_value(second.handle)
    assert registry.get_active_handle(project.project_gid) == first.handle
    # The webhook goes first; the stored value is deleted LAST.
    tail = [e for e in events if e[0] in ("asana_delete", "store_delete")]
    assert [kind for kind, _ in tail] == ["asana_delete", "store_delete"]
    assert tail[1] == ("store_delete", second.handle)
    assert all(w["target"].endswith(first.handle) for w in fake_asana.webhooks.values())


async def test_timeout_before_create_leaves_no_webhook(
    registrar: Registrar, registry: InMemoryHookRegistry, fake_asana: FakeAsana
) -> None:
    """OR-1 (D6 TDD fixture or review id)."""
    fake_asana.mode = "timeout_before_create"
    outcome = await registrar.register_project(project_with(TriggerKind.COMPLETION))
    assert outcome.status is RegistrationStatus.CREATE_UNKNOWN_DELETED
    record = registry.get_hook(outcome.handle)
    assert record is not None and record.state is HookState.REMOVED
    assert fake_asana.webhooks == {}


async def test_key_is_kept_while_the_webhook_delete_fails(
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    fake_asana: FakeAsana,
    clock: FakeClock,
) -> None:
    """OR-1: Key last: a failed webhook delete never leaves a live webhook without its value."""

    async def refuse_delete(gid: str) -> None:
        raise AsanaError("refused", status_code=403)

    fake_asana.delete_async = refuse_delete  # type: ignore[method-assign]
    reg = _registrar(WebhooksClient(sdk_client_backed_by(fake_asana)), registry, store, clock)
    project = project_with(TriggerKind.COMPLETION)
    await reg.register_project(project)  # holds the ACTIVE row
    fake_asana.mode = "timeout_after_create"
    with pytest.raises(WebhookCallFailed):
        await reg.register_project(project)
    handle = fake_asana.create_calls()[-1]["target"].rsplit("/", 1)[-1]
    record = registry.get_hook(handle)
    assert record is not None and record.state is HookState.CREATE_UNKNOWN
    assert store.has_value(handle)
    assert ("store_delete", handle) not in store.events


# ---------------------------------------------------------------------------
# Reconciler: lease, re-registration, one active per project, unowned webhooks
# ---------------------------------------------------------------------------


async def test_reconciler_skips_when_lease_held(
    registrar: Registrar, registry: InMemoryHookRegistry, clock: FakeClock, fake_asana: FakeAsana
) -> None:
    assert registry.acquire_lease(owner="other-task", now=int(clock()), duration_s=360)
    reconciler = Reconciler(
        registrar=registrar,
        registry=registry,
        projects=(project_with(TriggerKind.COMPLETION),),
        clock=clock,
        environ=SHADOW_TEST_ENV,
    )
    report = await reconciler.run_once()
    assert (report.ran, report.skipped_reason) == (False, "lease_held")
    assert fake_asana.calls == []
    clock.now += 361
    assert (await reconciler.run_once()).ran, "an expired lease is taken over"


class _Boom(RuntimeError):
    pass


async def test_run_forever_releases_the_lease_on_an_unexpected_exception(
    registrar: Registrar, registry: InMemoryHookRegistry, clock: FakeClock
) -> None:
    """warden-bench F-6: an exception ends run_forever, and the lease is released anyway."""
    import asyncio

    reconciler = Reconciler(
        registrar=registrar,
        registry=registry,
        projects=(project_with(TriggerKind.COMPLETION),),
        clock=clock,
        environ=SHADOW_TEST_ENV,
    )

    async def explode() -> Any:
        assert registry.acquire_lease(owner=reconciler.owner, now=int(clock()), duration_s=360)
        raise _Boom("unexpected")

    reconciler.run_once = explode  # type: ignore[method-assign]
    with pytest.raises(_Boom):
        await reconciler.run_forever(asyncio.Event())
    # Released: another owner takes it at once, without waiting for expiry.
    assert registry.acquire_lease(owner="next-task", now=int(clock()), duration_s=360)


async def test_run_forever_releases_the_lease_on_a_clean_stop(
    registrar: Registrar, registry: InMemoryHookRegistry, clock: FakeClock
) -> None:
    """warden-bench F-6 twin (D6 TDD fixture or review id)."""
    import asyncio

    reconciler = Reconciler(
        registrar=registrar, registry=registry, projects=(), clock=clock, environ=SHADOW_TEST_ENV
    )
    stop = asyncio.Event()

    async def once_then_stop() -> Any:
        assert registry.acquire_lease(owner=reconciler.owner, now=int(clock()), duration_s=360)
        stop.set()

    reconciler.run_once = once_then_stop  # type: ignore[method-assign]
    await reconciler.run_forever(stop)
    assert registry.acquire_lease(owner="next-task", now=int(clock()), duration_s=360)


async def test_a_held_lease_blocks_another_owner(
    registry: InMemoryHookRegistry, clock: FakeClock
) -> None:
    """warden-bench F-6 teeth: Without a release, the next owner is refused until expiry: the probe has teeth."""
    assert registry.acquire_lease(owner="first", now=int(clock()), duration_s=360)
    assert not registry.acquire_lease(owner="next-task", now=int(clock()), duration_s=360)


async def test_reconcile_replaces_unhealthy_hook_and_retires_old(
    registrar: Registrar,
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    fake_asana: FakeAsana,
) -> None:
    project = project_with(TriggerKind.COMPLETION)
    old = await registrar.register_project(project)
    old_record = registry.get_hook(old.handle)
    assert old_record is not None and old_record.webhook_gid is not None
    fake_asana.inactive.add(old_record.webhook_gid)  # Asana deactivated it
    outcomes = await registrar.reconcile_project(project)
    assert [o.status for o in outcomes] == [RegistrationStatus.ACTIVE]
    new_handle = outcomes[0].handle
    assert registry.get_active_handle(project.project_gid) == new_handle
    retired = registry.get_hook(old.handle)
    assert retired is not None and retired.state is HookState.REMOVED
    assert not store.has_value(old.handle) and store.has_value(new_handle)
    assert old_record.webhook_gid not in fake_asana.webhooks


async def test_reconcile_twin_healthy_hook_is_left_alone(
    registrar: Registrar, fake_asana: FakeAsana
) -> None:
    project = project_with(TriggerKind.COMPLETION)
    await registrar.register_project(project)
    assert await registrar.reconcile_project(project) == []
    assert len(fake_asana.create_calls()) == 1


async def test_reconcile_never_deletes_an_unowned_webhook(
    registrar: Registrar, fake_asana: FakeAsana
) -> None:
    project = project_with(TriggerKind.COMPLETION)
    await registrar.register_project(project)
    # Our target shape, but no registry row: not provably ours.
    planted = fake_asana.plant(
        target=f"{TARGET_BASE}/{secrets.token_hex(16)}", resource=project.project_gid
    )
    await registrar.reconcile_project(project)
    assert planted in fake_asana.webhooks


async def test_reconcile_retires_our_stale_orphan(
    registrar: Registrar,
    registry: InMemoryHookRegistry,
    fake_asana: FakeAsana,
    clock: FakeClock,
    hex_handle: str,
) -> None:
    project = project_with(TriggerKind.COMPLETION)
    await registrar.register_project(project)
    registry.put_pending(handle=hex_handle, resource_gid=project.project_gid, now=int(clock()))
    orphan = fake_asana.plant(target=f"{TARGET_BASE}/{hex_handle}", resource=project.project_gid)
    await registrar.reconcile_project(project)
    assert orphan in fake_asana.webhooks, "an in-flight registration is not touched"
    clock.now += 61
    await registrar.reconcile_project(project)
    assert orphan not in fake_asana.webhooks
    record = registry.get_hook(hex_handle)
    assert record is not None and record.state is HookState.REMOVED


def test_registration_never_logs_the_handle() -> None:
    """auth-bench A3-1: no logger call in registration passes the handle as a value.

    Log lines carry ``handle_fp`` (hook_store.handle_fingerprint), never the handle.
    """
    tree = ast.parse(Path(registration_module.__file__).read_text())
    calls = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if getattr(node.func.value, "id", None) == "logger":
                calls += 1
                for value in ast.walk(node):
                    if isinstance(value, ast.Dict):
                        for key, item in zip(value.keys, value.values):
                            if isinstance(item, ast.Name) and item.id in ("handle", "active"):
                                raise AssertionError(ast.unparse(node))
                            assert not (isinstance(key, ast.Constant) and key.value == "handle"), (
                                ast.unparse(node)
                            )
    assert calls > 10, "positive control: the scan saw registration's logger calls"


def test_handshake_value_never_logged() -> None:
    """AST: no logger call in registration passes the header or echo as a field."""
    tree = ast.parse(Path(registration_module.__file__).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if getattr(node.func.value, "id", None) == "logger":
                names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
                assert not names & {"hook_header", "echo"}, ast.unparse(node)


def test_sdk_client_class_is_the_one_checked() -> None:
    assert SdkWebhooksClient.__module__ == "autom8_asana.clients.webhooks"
