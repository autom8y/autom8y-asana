"""Fixtures for the D6 registration tests.

All identifiers, handles and hook values are generated at runtime. Nothing here reaches
AWS or Asana: DynamoDB is moto's in-memory backend and Asana is :class:`FakeAsana`.
"""

from __future__ import annotations

import asyncio
import secrets
import time
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import boto3
import pytest
from moto import mock_aws

from autom8_asana.clients.webhooks import WebhooksClient as SdkWebhooksClient
from autom8_asana.core.types import EntityType
from autom8_asana.errors import AsanaError, NotFoundError
from autom8_asana.trigger.ports_webhooks import WebhooksClient
from autom8_asana.trigger.registration import Registrar, handle_handshake
from autom8_asana.trigger.watched_projects import TriggerKind, WatchedProject
from tests.unit.trigger.adapters import TEST_REGION, InMemoryHookRegistry, InMemoryKeyHookStore

if TYPE_CHECKING:
    from collections.abc import Iterator

TARGET_BASE = "https://hooks.example.com/api/v1/webhooks/asana"
TEST_ENV = {"ASANA_HOOK_ENVIRONMENT": "test"}
SHADOW_TEST_ENV = {"ASANA_HOOK_ENVIRONMENT": "test", "ASANA_HOOK_SHADOW_ENABLED": "1"}


def runtime_gid() -> str:
    """A 16-digit Asana-shaped gid, generated at runtime."""
    low = 10 ** (16 - 1)
    return str(low + secrets.randbelow(9 * low))


def runtime_hook_value() -> str:
    """A handshake value of the documented shape, generated at runtime."""
    return secrets.token_urlsafe(32)


class LogSpy:
    """Captures ``logger.<level>(event, extra=...)`` calls (autom8y_log bypasses caplog)."""

    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, Any]]] = []

    def _record(self, level: str) -> Any:
        def record(event: str, *args: Any, **kwargs: Any) -> None:
            self.events.append((level, event, dict(kwargs.get("extra") or {})))

        return record

    def __getattr__(self, level: str) -> Any:
        return self._record(level)

    def named(self, event: str) -> list[dict[str, Any]]:
        return [extra for _, name, extra in self.events if name == event]


@dataclass
class FakeClock:
    now: float = field(default_factory=lambda: float(int(time.time())))

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def aws_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        monkeypatch.setenv(name, "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", TEST_REGION)
    with mock_aws():
        yield


@pytest.fixture
def ddb_client(aws_env: None) -> Any:
    return boto3.client("dynamodb", region_name=TEST_REGION)


@pytest.fixture
def registry(ddb_client: Any) -> InMemoryHookRegistry:
    return InMemoryHookRegistry(client=ddb_client, environ=TEST_ENV)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def events() -> list[tuple[str, str]]:
    return []


@pytest.fixture
def store(events: list[tuple[str, str]]) -> InMemoryKeyHookStore:
    return InMemoryKeyHookStore(environ=TEST_ENV, events=events)


class FakeAsana:
    """Stands in for Asana's /webhooks API, including the handshake during create.

    ``mode`` selects create behavior: ``ok``; ``timeout_after_create`` (Asana created the
    webhook, the caller sees a timeout, OR-1); ``timeout_before_create`` (nothing was
    created); ``refuse`` (a definite 400).
    """

    def __init__(
        self,
        *,
        registry: Any,
        store: Any,
        clock: FakeClock,
        events: list[tuple[str, str]],
    ) -> None:
        self.registry = registry
        self.store = store
        self.clock = clock
        self.events = events
        self.webhooks: dict[str, dict[str, Any]] = {}
        self.calls: list[tuple[str, Any]] = []
        self.mode = "ok"
        self.inactive: set[str] = set()

    async def create_async(
        self, *, resource: str, target: str, raw: bool, filters: list[dict[str, Any]]
    ) -> dict[str, Any]:
        self.calls.append(("create", {"resource": resource, "target": target, "filters": filters}))
        if self.mode == "timeout_before_create":
            raise TimeoutError
        if self.mode == "refuse":
            raise AsanaError("refused", status_code=400)
        handle = target.rsplit("/", 1)[-1]
        sent = runtime_hook_value()
        result = await handle_handshake(
            handle=handle,
            hook_header=sent,
            registry=self.registry,
            store=self.store,
            now=int(self.clock()),
        )
        if result.status_code != 200 or result.echo != sent:
            raise AsanaError("handshake failed", status_code=400)
        gid = runtime_gid()
        self.webhooks[gid] = {
            "gid": gid,
            "target": target,
            "resource": {"gid": resource},
            "active": True,
            "last_success_at": None,
            "last_failure_at": None,
        }
        if self.mode == "timeout_after_create":
            raise TimeoutError
        return dict(self.webhooks[gid])

    def plant(self, *, target: str, resource: str) -> str:
        gid = runtime_gid()
        self.webhooks[gid] = {
            "gid": gid,
            "target": target,
            "resource": {"gid": resource},
            "active": True,
            "last_success_at": None,
            "last_failure_at": None,
        }
        return gid

    async def get_async(self, gid: str, *, raw: bool, opt_fields: list[str]) -> dict[str, Any]:
        self.calls.append(("get", gid))
        if gid not in self.webhooks:
            raise NotFoundError("not found", status_code=404)
        data = dict(self.webhooks[gid])
        if gid in self.inactive:
            data["active"] = False
        return data

    async def delete_async(self, gid: str) -> None:
        self.calls.append(("delete", gid))
        self.events.append(("asana_delete", gid))
        if gid not in self.webhooks:
            raise NotFoundError("not found", status_code=404)
        del self.webhooks[gid]

    def list_for_workspace_async(
        self, workspace: str, *, resource: str | None, opt_fields: list[str]
    ) -> Any:
        self.calls.append(("list", resource))
        found = [
            SimpleNamespace(
                gid=w["gid"],
                target=w["target"],
                resource=SimpleNamespace(gid=w["resource"]["gid"]),
                active=w["gid"] not in self.inactive,
                last_success_at=None,
                last_failure_at=None,
            )
            for w in self.webhooks.values()
            if resource is None or w["resource"]["gid"] == resource
        ]

        async def collect() -> list[Any]:
            return found

        return SimpleNamespace(collect=collect)

    def create_calls(self) -> list[dict[str, Any]]:
        return [args for name, args in self.calls if name == "create"]


def sdk_client_backed_by(fake: FakeAsana) -> SdkWebhooksClient:
    """A real SDK webhooks-client instance whose four calls go to ``fake``."""
    inner = SdkWebhooksClient.__new__(SdkWebhooksClient)
    inner.create_async = fake.create_async  # type: ignore[method-assign]
    inner.get_async = fake.get_async  # type: ignore[method-assign]
    inner.delete_async = fake.delete_async  # type: ignore[method-assign]
    inner.list_for_workspace_async = fake.list_for_workspace_async  # type: ignore[method-assign]
    return inner


@pytest.fixture
def fake_asana(
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    clock: FakeClock,
    events: list[tuple[str, str]],
) -> FakeAsana:
    return FakeAsana(registry=registry, store=store, clock=clock, events=events)


@pytest.fixture
def port(fake_asana: FakeAsana) -> WebhooksClient:
    return WebhooksClient(sdk_client_backed_by(fake_asana))


@pytest.fixture
def hex_handle() -> str:
    return secrets.token_hex(16)


@pytest.fixture
def workspace_gid() -> str:
    return runtime_gid()


@pytest.fixture
def registrar(
    port: WebhooksClient,
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    clock: FakeClock,
    workspace_gid: str,
) -> Registrar:
    return Registrar(
        webhooks=port,
        registry=registry,
        store=store,
        workspace_gid=workspace_gid,
        target_base_url=TARGET_BASE,
        clock=clock,
        environ=SHADOW_TEST_ENV,
    )


def project_with(*kinds: TriggerKind) -> WatchedProject:
    return WatchedProject(
        entity_type=EntityType.OFFER, project_gid=runtime_gid(), trigger_kinds=tuple(kinds)
    )
