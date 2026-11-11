"""``WebhooksClient``: the narrow /webhooks port for D6 registration (A C-12).

Design of record: TDD-asana-bench-D6-shadow-receiver-20261110 r4.6, section 2.

The port exposes four operations and nothing else: create, get, list (for one resource)
and delete of ``/webhooks``. It wraps exactly the SDK's full-CRUD
``autom8_asana.clients.webhooks.WebhooksClient`` and exposes no attribute of it: no
``update``, no ``_http``, no passthrough ``__getattr__``. Results are plain frozen
values, never SDK models.

The wrapped class is checked by identity at construction. The check resolves the class
from ``sys.modules`` instead of importing it, so this module adds no edge to the SDK
client graph; an instance of the class can exist only if its module is loaded.
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from autom8_asana.errors import (
    AsanaError,
    GoneError,
    NotFoundError,
    RateLimitError,
    ServerError,
)
from autom8_asana.errors import TimeoutError as AsanaTimeoutError

_FULL_CLIENT_MODULE: Final[str] = "autom8_asana.clients.webhooks"
_FULL_CLIENT_NAME: Final[str] = "WebhooksClient"
_OPT_FIELDS: Final[list[str]] = [
    "target",
    "active",
    "resource",
    "last_success_at",
    "last_failure_at",
]


class WebhooksPortRefused(TypeError):
    """The port was given anything other than the SDK's webhooks resource client."""


class WebhookCallFailed(RuntimeError):
    """An Asana /webhooks call failed with a definite answer."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class WebhookCallOutcomeUnknown(WebhookCallFailed):
    """The call may or may not have taken effect (timeout, 5xx, rate limit, transport)."""


@dataclass(frozen=True)
class WebhookView:
    """The fields registration reads from a webhook. Never an SDK object."""

    gid: str
    target: str | None
    resource_gid: str | None
    active: bool | None
    last_success_at: str | None
    last_failure_at: str | None


def _view_from_mapping(data: Mapping[str, Any]) -> WebhookView:
    resource = data.get("resource")
    resource_gid = resource.get("gid") if isinstance(resource, Mapping) else None
    gid = data.get("gid")
    if not isinstance(gid, str) or not gid:
        raise WebhookCallFailed("Asana returned a webhook without a gid")
    return WebhookView(
        gid=gid,
        target=data.get("target"),
        resource_gid=resource_gid if isinstance(resource_gid, str) else None,
        active=data.get("active"),
        last_success_at=data.get("last_success_at"),
        last_failure_at=data.get("last_failure_at"),
    )


def _view_from_model(model: Any) -> WebhookView:
    resource = getattr(model, "resource", None)
    return _view_from_mapping(
        {
            "gid": getattr(model, "gid", None),
            "target": getattr(model, "target", None),
            "resource": {"gid": getattr(resource, "gid", None)} if resource is not None else None,
            "active": getattr(model, "active", None),
            "last_success_at": getattr(model, "last_success_at", None),
            "last_failure_at": getattr(model, "last_failure_at", None),
        }
    )


def _classify(operation: str, exc: BaseException) -> WebhookCallFailed:
    if isinstance(exc, (asyncio.TimeoutError, AsanaTimeoutError, ServerError, RateLimitError)):
        status = getattr(exc, "status_code", None)
        return WebhookCallOutcomeUnknown(
            f"{operation}: outcome unknown ({type(exc).__name__})", status_code=status
        )
    if isinstance(exc, AsanaError):
        return WebhookCallFailed(
            f"{operation}: refused by Asana ({type(exc).__name__})", status_code=exc.status_code
        )
    # Transport errors below the SDK's own classification: the request may have landed.
    return WebhookCallOutcomeUnknown(f"{operation}: outcome unknown ({type(exc).__name__})")


def _full_client_class() -> type | None:
    module = sys.modules.get(_FULL_CLIENT_MODULE)
    cls = getattr(module, _FULL_CLIENT_NAME, None) if module is not None else None
    return cls if isinstance(cls, type) else None


class WebhooksClient:
    """create / get / list / delete of ``/webhooks``, and nothing else."""

    __slots__ = ("__inner",)
    __inner: Any

    def __init__(self, inner: Any) -> None:
        expected = _full_client_class()
        if expected is None or type(inner) is not expected:
            raise WebhooksPortRefused(
                "WebhooksClient wraps only autom8_asana.clients.webhooks.WebhooksClient, "
                f"not {type(inner).__module__}.{type(inner).__qualname__}"
            )
        self.__inner = inner

    async def create(
        self, *, resource_gid: str, target: str, filters: Sequence[Mapping[str, Any]]
    ) -> WebhookView:
        try:
            data = await self.__inner.create_async(
                resource=resource_gid,
                target=target,
                raw=True,
                filters=[dict(f) for f in filters],
            )
        except Exception as exc:  # noqa: BLE001
            # BROAD-CATCH: boundary -- classified into definite vs unknown outcome.
            raise _classify("create", exc) from None
        return _view_from_mapping(data)

    async def get(self, webhook_gid: str) -> WebhookView | None:
        """The webhook, or ``None`` when Asana says it does not exist (404 or 410)."""
        try:
            data = await self.__inner.get_async(webhook_gid, raw=True, opt_fields=_OPT_FIELDS)
        except (NotFoundError, GoneError):
            return None
        except Exception as exc:  # noqa: BLE001
            # BROAD-CATCH: boundary -- classified, never swallowed.
            raise _classify("get", exc) from None
        return _view_from_mapping(data)

    async def list_for_resource(
        self, *, workspace_gid: str, resource_gid: str
    ) -> list[WebhookView]:
        try:
            models = await self.__inner.list_for_workspace_async(
                workspace_gid, resource=resource_gid, opt_fields=_OPT_FIELDS
            ).collect()
        except Exception as exc:  # noqa: BLE001
            # BROAD-CATCH: boundary -- classified, never swallowed.
            raise _classify("list", exc) from None
        return [_view_from_model(m) for m in models]

    async def delete(self, webhook_gid: str) -> bool:
        """``True`` on delete, ``False`` when the webhook was already gone."""
        try:
            await self.__inner.delete_async(webhook_gid)
        except (NotFoundError, GoneError):
            return False
        except Exception as exc:  # noqa: BLE001
            # BROAD-CATCH: boundary -- classified, never swallowed.
            raise _classify("delete", exc) from None
        return True
