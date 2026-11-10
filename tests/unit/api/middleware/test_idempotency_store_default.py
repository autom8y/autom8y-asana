"""Idempotency store-and-replay is opt-in.

With no backend configured, the app wires the passthrough store, so no request
reads or writes an idempotency record. Configuring a backend still opts in.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8_asana.api import main as api_main
from autom8_asana.api.middleware.idempotency import (
    IdempotencyMiddleware,
    InMemoryIdempotencyStore,
    NoopIdempotencyStore,
)

if TYPE_CHECKING:
    import pytest


def _wired_store(monkeypatch: pytest.MonkeyPatch, backend: str | None) -> object:
    if backend is None:
        monkeypatch.delenv("IDEMPOTENCY_STORE_BACKEND", raising=False)
    else:
        monkeypatch.setenv("IDEMPOTENCY_STORE_BACKEND", backend)
    app = api_main.create_app()
    stores = [mw.kwargs["store"] for mw in app.user_middleware if mw.cls is IdempotencyMiddleware]
    assert len(stores) == 1
    return stores[0]


def test_default_backend_constant_is_passthrough() -> None:
    assert api_main.DEFAULT_IDEMPOTENCY_BACKEND == "noop"


def test_unconfigured_app_wires_passthrough_store(monkeypatch: pytest.MonkeyPatch) -> None:
    assert isinstance(_wired_store(monkeypatch, None), NoopIdempotencyStore)


def test_configured_backend_still_opts_in(monkeypatch: pytest.MonkeyPatch) -> None:
    assert isinstance(_wired_store(monkeypatch, "memory"), InMemoryIdempotencyStore)
