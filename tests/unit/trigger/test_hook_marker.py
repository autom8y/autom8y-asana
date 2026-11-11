"""The ``ASANA_HOOK_ENVIRONMENT`` marker: fixtures PM-1, PM-3, PM-5 (TDD r4.6 section 2a).

Built to the TDD body, section 2a "The marker (W D-2)", per auth-bench A2-1: the marker
has a positive value on each side, and absent refuses both sides.

Every refusal asserts the typed error, exactly one log event that names the variable and
the condition (never the value), and that no write reached the client. Every positive
twin asserts that the write DID reach the client, so a silent no-op writer fails it.
"""

from __future__ import annotations

from typing import Any

import pytest

from autom8_asana.trigger import hook_environment, hook_store
from autom8_asana.trigger.hook_environment import (
    MARKER_ENV_VAR,
    HookEnvironmentRefused,
    MarkerCondition,
    assert_shadow_startup,
)
from autom8_asana.trigger.hook_store import HookStore, HookStoreRefused
from tests.unit.trigger.adapters import InMemoryHookRegistry, InMemoryKeyHookStore
from tests.unit.trigger.conftest import LogSpy

TASK_ROLE_ENV = {
    "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI": "/v2/task-role",
    "ECS_CONTAINER_METADATA_URI_V4": "http://metadata.example.com/v4/task",
}

# PM-3 (auth A2 condition) plus auth-bench A2-2's production variants.
_REFUSED_PRESENT: list[tuple[str, MarkerCondition]] = [
    ("", MarkerCondition.EMPTY),
    ("staging", MarkerCondition.UNRECOGNIZED),
    ("prod", MarkerCondition.UNRECOGNIZED),
    ("Production", MarkerCondition.UNRECOGNIZED),
    ("PRODUCTION", MarkerCondition.UNRECOGNIZED),
    (" production", MarkerCondition.UNRECOGNIZED),
    ("production\n", MarkerCondition.UNRECOGNIZED),
    ("TEST", MarkerCondition.UNRECOGNIZED),
    (" local ", MarkerCondition.UNRECOGNIZED),
    ("local\n", MarkerCondition.UNRECOGNIZED),
    ("lcoal", MarkerCondition.UNRECOGNIZED),
]
REFUSED_MARKERS: list[tuple[dict[str, str], MarkerCondition]] = [
    ({}, MarkerCondition.ABSENT),
    *(({MARKER_ENV_VAR: value}, condition) for value, condition in _REFUSED_PRESENT),
]
REFUSED_IDS = ["absent", *(repr(v) for v, _ in _REFUSED_PRESENT)]


class RecordingSecretsClient:
    """Records every call. If a refused posture ever reached it, the test fails."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def create_secret(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("create_secret", kwargs))
        return {"Name": kwargs["Name"]}

    def tag_resource(self, **kwargs: Any) -> None:
        self.calls.append(("tag_resource", kwargs))

    def delete_secret(self, **kwargs: Any) -> None:
        self.calls.append(("delete_secret", kwargs))


@pytest.fixture
def env_log(monkeypatch: pytest.MonkeyPatch) -> LogSpy:
    spy = LogSpy()
    monkeypatch.setattr(hook_environment, "logger", spy)
    return spy


@pytest.fixture
def store_log(monkeypatch: pytest.MonkeyPatch) -> LogSpy:
    spy = LogSpy()
    monkeypatch.setattr(hook_store, "logger", spy)
    return spy


def _write(store: HookStore, handle: str, value: str) -> None:
    store.create_hook_value(
        handle=handle,
        hook_value=value,
        resource_gid="resource",
        registered_at="2026-11-11T00:00:00+00:00",
    )


def _assert_one_refusal_event(
    spy: LogSpy, condition: MarkerCondition, marker: dict[str, str]
) -> None:
    assert len(spy.events) == 1, spy.events
    level, event, extra = spy.events[0]
    assert (level, event) == ("error", "hook_environment_refused")
    assert extra["variable"] == MARKER_ENV_VAR
    assert extra["condition"] == condition.value
    raw = marker.get(MARKER_ENV_VAR)
    if raw:
        assert raw not in extra.values(), "the marker value must never be logged"


# ---------------------------------------------------------------------------
# PM-3: every unrecognized value refuses BOTH sides
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("marker", "condition"), REFUSED_MARKERS, ids=REFUSED_IDS)
def test_pm3_store_refuses(
    marker: dict[str, str], condition: MarkerCondition, env_log: LogSpy, hex_handle: str
) -> None:
    client = RecordingSecretsClient()
    with pytest.raises(HookEnvironmentRefused) as caught:
        store = HookStore(client=client, environ={**marker, **TASK_ROLE_ENV})
        _write(store, hex_handle, "unwritten")
    assert caught.value.condition is condition
    assert client.calls == []
    _assert_one_refusal_event(env_log, condition, marker)


@pytest.mark.parametrize(("marker", "condition"), REFUSED_MARKERS, ids=REFUSED_IDS)
def test_pm3_key_store_adapter_refuses(
    marker: dict[str, str], condition: MarkerCondition, env_log: LogSpy
) -> None:
    with pytest.raises(HookEnvironmentRefused) as caught:
        InMemoryKeyHookStore(environ=marker)
    assert caught.value.condition is condition
    _assert_one_refusal_event(env_log, condition, marker)


@pytest.mark.parametrize(("marker", "condition"), REFUSED_MARKERS, ids=REFUSED_IDS)
def test_pm3_registry_adapter_refuses(
    marker: dict[str, str], condition: MarkerCondition, env_log: LogSpy, ddb_client: Any
) -> None:
    with pytest.raises(HookEnvironmentRefused) as caught:
        InMemoryHookRegistry(client=ddb_client, environ=marker)
    assert caught.value.condition is condition
    assert ddb_client.list_tables()["TableNames"] == [], "refused before creating anything"
    _assert_one_refusal_event(env_log, condition, marker)


@pytest.mark.parametrize(("marker", "condition"), REFUSED_MARKERS, ids=REFUSED_IDS)
def test_pm3_shadow_startup_fails(
    marker: dict[str, str], condition: MarkerCondition, env_log: LogSpy
) -> None:
    with pytest.raises(HookEnvironmentRefused) as caught:
        assert_shadow_startup({**marker, "ASANA_HOOK_SHADOW_ENABLED": "1"})
    assert caught.value.condition is condition
    _assert_one_refusal_event(env_log, condition, marker)


@pytest.mark.parametrize("value", ["test", "local"])
def test_pm3_twin_exact_test_and_local_build_adapters(
    value: str, env_log: LogSpy, ddb_client: Any
) -> None:
    InMemoryKeyHookStore(environ={MARKER_ENV_VAR: value})
    InMemoryHookRegistry(client=ddb_client, environ={MARKER_ENV_VAR: value})
    assert env_log.events == []


def test_pm3_twin_exact_production_writes(
    env_log: LogSpy, store_log: LogSpy, hex_handle: str
) -> None:
    client = RecordingSecretsClient()
    store = HookStore(client=client, environ={MARKER_ENV_VAR: "production", **TASK_ROLE_ENV})
    _write(store, hex_handle, "written")
    assert [name for name, _ in client.calls] == ["create_secret"]
    assert client.calls[0][1]["Name"] == f"autom8y/asana/webhook-hook/{hex_handle}"
    assert env_log.events == []


def test_pm3_twin_shadow_startup_passes_on_exact_values(env_log: LogSpy) -> None:
    for value in ("production", "test", "local"):
        flag = {MARKER_ENV_VAR: value, "ASANA_HOOK_SHADOW_ENABLED": "1"}
        assert assert_shadow_startup(flag) is not None
    assert assert_shadow_startup({}) is None, "shadow off reads nothing and returns None"
    assert env_log.events == []


# ---------------------------------------------------------------------------
# PM-1: production refuses the test adapters
# ---------------------------------------------------------------------------


def test_pm1_production_refuses_key_store_adapter(env_log: LogSpy) -> None:
    with pytest.raises(HookEnvironmentRefused) as caught:
        InMemoryKeyHookStore(environ={MARKER_ENV_VAR: "production"})
    assert caught.value.condition is MarkerCondition.WRONG_SIDE
    assert len(env_log.named("hook_environment_refused")) == 1


def test_pm1_production_refuses_registry_adapter(env_log: LogSpy, ddb_client: Any) -> None:
    with pytest.raises(HookEnvironmentRefused):
        InMemoryHookRegistry(client=ddb_client, environ={MARKER_ENV_VAR: "production"})
    assert ddb_client.list_tables()["TableNames"] == []
    assert len(env_log.named("hook_environment_refused")) == 1


def test_pm1_twin_test_marker_builds_adapters(ddb_client: Any) -> None:
    InMemoryKeyHookStore(environ={MARKER_ENV_VAR: "test"})
    InMemoryHookRegistry(client=ddb_client, environ={MARKER_ENV_VAR: "test"})


# ---------------------------------------------------------------------------
# PM-5: test/local markers refuse the store write
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["test", "local"])
@pytest.mark.parametrize("operation", ["create", "tag", "delete"])
def test_pm5_test_marker_refuses_every_store_call(
    value: str, operation: str, store_log: LogSpy, hex_handle: str
) -> None:
    client = RecordingSecretsClient()
    store = HookStore(client=client, environ={MARKER_ENV_VAR: value, **TASK_ROLE_ENV})
    with pytest.raises(HookStoreRefused):
        if operation == "create":
            _write(store, hex_handle, "unwritten")
        elif operation == "tag":
            store.tag_webhook_gid(handle=hex_handle, webhook_gid="w")
        else:
            store.delete_hook_value(handle=hex_handle)
    assert client.calls == []
    refusals = store_log.named("hook_store_refused")
    assert refusals == [{"operation": operation, "reason": "marker_not_production"}]


def test_pm5_twin_production_writes(hex_handle: str) -> None:
    client = RecordingSecretsClient()
    store = HookStore(client=client, environ={MARKER_ENV_VAR: "production", **TASK_ROLE_ENV})
    _write(store, hex_handle, "written")
    store.tag_webhook_gid(handle=hex_handle, webhook_gid="w")
    assert store.delete_hook_value(handle=hex_handle) is True
    assert [n for n, _ in client.calls] == ["create_secret", "tag_resource", "delete_secret"]
    assert client.calls[2][1]["RecoveryWindowInDays"] == 7


# ---------------------------------------------------------------------------
# production with a failing task-role check still refuses
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "credentials",
    [
        {},
        {"AWS_CONTAINER_CREDENTIALS_RELATIVE_URI": "/v2/task-role"},
        {**TASK_ROLE_ENV, "AWS_PROFILE": "laptop"},
        {**TASK_ROLE_ENV, "AWS_ACCESS_KEY_ID": "outranking"},
    ],
    ids=["no-task-role", "no-metadata", "profile-outranks", "env-keys-outrank"],
)
def test_production_with_failing_task_role_check_refuses(
    credentials: dict[str, str], store_log: LogSpy, hex_handle: str
) -> None:
    client = RecordingSecretsClient()
    store = HookStore(client=client, environ={MARKER_ENV_VAR: "production", **credentials})
    with pytest.raises(HookStoreRefused) as caught:
        _write(store, hex_handle, "unwritten")
    assert client.calls == []
    assert store_log.named("hook_store_refused") == [
        {"operation": "create", "reason": "task_role_check_failed"}
    ]
    assert "outranking" not in str(caught.value) and "laptop" not in str(caught.value)


def test_marker_is_read_once_at_construction(hex_handle: str) -> None:
    environ = {MARKER_ENV_VAR: "test", **TASK_ROLE_ENV}
    client = RecordingSecretsClient()
    store = HookStore(client=client, environ=environ)
    environ[MARKER_ENV_VAR] = "production"  # a later change does not reopen the store
    with pytest.raises(HookStoreRefused):
        _write(store, hex_handle, "unwritten")
    assert client.calls == []


def test_store_code_never_reads_the_retired_gate_name() -> None:
    from pathlib import Path

    trigger = Path(hook_store.__file__).parent
    retired = "ASANA_WEBHOOK_HOOK_SM_" + "ENABLED"
    offenders = [p.name for p in trigger.glob("*.py") if retired in p.read_text()]
    assert offenders == []
