"""``trigger.ports_webhooks.WebhooksClient``: four operations, nothing else (A C-12)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from autom8_asana.client import AsanaClient
from autom8_asana.clients.webhooks import WebhooksClient as SdkWebhooksClient
from autom8_asana.errors import AsanaError, NotFoundError, ServerError
from autom8_asana.trigger.ports_webhooks import (
    WebhookCallFailed,
    WebhookCallOutcomeUnknown,
    WebhooksClient,
    WebhooksPortRefused,
    WebhookView,
)
from tests.unit.trigger.conftest import FakeAsana, runtime_gid, sdk_client_backed_by

PUBLIC_SURFACE = {"create", "get", "list_for_resource", "delete"}


def test_port_surface_is_exactly_four_operations(port: WebhooksClient) -> None:
    public = {name for name in dir(port) if not name.startswith("_")}
    assert public == PUBLIC_SURFACE
    for absent in ("update", "update_async", "_http", "_config", "_auth_provider", "webhooks"):
        assert not hasattr(port, absent), absent
    assert "__getattr__" not in type(port).__dict__
    assert not hasattr(port, "__dict__"), "slots only: no attribute can be attached"


def test_port_refuses_full_asana_client() -> None:
    with pytest.raises(WebhooksPortRefused):
        WebhooksClient(AsanaClient.__new__(AsanaClient))


def test_port_refuses_a_subclass_or_lookalike() -> None:
    class Sub(SdkWebhooksClient):
        pass

    class Lookalike:
        __module__ = "autom8_asana.clients.webhooks"
        __qualname__ = "WebhooksClient"

    with pytest.raises(WebhooksPortRefused):
        WebhooksClient(Sub.__new__(Sub))
    with pytest.raises(WebhooksPortRefused):
        WebhooksClient(Lookalike())


def test_port_twin_accepts_the_sdk_webhooks_client(fake_asana: FakeAsana) -> None:
    assert isinstance(WebhooksClient(sdk_client_backed_by(fake_asana)), WebhooksClient)


class _Raising:
    def __init__(self, exc: BaseException) -> None:
        self.exc = exc

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        raise self.exc


@pytest.mark.parametrize(
    ("exc", "unknown"),
    [
        (TimeoutError(), True),
        (ServerError("down", status_code=503), True),
        (ConnectionError("reset"), True),
        (AsanaError("bad request", status_code=400), False),
    ],
)
async def test_create_classifies_definite_vs_unknown(
    fake_asana: FakeAsana, exc: BaseException, unknown: bool
) -> None:
    inner = sdk_client_backed_by(fake_asana)
    inner.create_async = _Raising(exc)  # type: ignore[method-assign]
    port = WebhooksClient(inner)
    with pytest.raises(WebhookCallFailed) as caught:
        await port.create(resource_gid=runtime_gid(), target="https://x", filters=[])
    assert isinstance(caught.value, WebhookCallOutcomeUnknown) is unknown


async def test_get_and_delete_treat_not_found_as_absent(fake_asana: FakeAsana) -> None:
    inner = sdk_client_backed_by(fake_asana)
    inner.get_async = _Raising(NotFoundError("gone", status_code=404))  # type: ignore[method-assign]
    inner.delete_async = _Raising(NotFoundError("gone", status_code=404))  # type: ignore[method-assign]
    port = WebhooksClient(inner)
    assert await port.get(runtime_gid()) is None
    assert await port.delete(runtime_gid()) is False


async def test_list_returns_plain_views(port: WebhooksClient, fake_asana: FakeAsana) -> None:
    project = runtime_gid()
    gid = fake_asana.plant(target="https://hooks.example.com/t", resource=project)
    views = await port.list_for_resource(workspace_gid=runtime_gid(), resource_gid=project)
    assert views == [
        WebhookView(
            gid=gid,
            target="https://hooks.example.com/t",
            resource_gid=project,
            active=True,
            last_success_at=None,
            last_failure_at=None,
        )
    ]
