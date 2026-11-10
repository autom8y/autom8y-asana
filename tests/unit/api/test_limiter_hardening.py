"""Rate-limiter hardening: pinned storage and a namespace-only 429 log line."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from starlette.requests import Request

from autom8_asana.api import errors, rate_limit

if TYPE_CHECKING:
    import pytest


def test_limiter_storage_uri_is_pinned_in_process() -> None:
    assert rate_limit.LIMITER_STORAGE_URI == "memory://"
    assert rate_limit.limiter._storage_uri == rate_limit.LIMITER_STORAGE_URI


def test_build_limiter_passes_explicit_storage_uri() -> None:
    assert rate_limit._build_limiter()._storage_uri == rate_limit.LIMITER_STORAGE_URI


class _RecordingLogger:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def info(self, event: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append((event, {"args": args, **kwargs}))


def test_429_handler_logs_namespace_but_never_the_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import slowapi

    secret_detail = "abcdef0123456789"
    monkeypatch.setattr(rate_limit, "_get_rate_limit_key", lambda request: f"pat:{secret_detail}")
    monkeypatch.setattr(slowapi, "_rate_limit_exceeded_handler", lambda request, exc: "upstream")
    recorder = _RecordingLogger()
    monkeypatch.setattr(errors, "logger", recorder)

    request = Request({"type": "http", "method": "POST", "path": "/x", "headers": []})
    result = asyncio.run(errors.rate_limit_exceeded_namespace_handler(request, Exception()))

    assert result == "upstream"
    events = [c for c in recorder.calls if c[0] == "rate_limit_exceeded"]
    assert len(events) == 1
    assert events[0][1]["extra"] == {"namespace": "pat", "method": "POST"}
    assert secret_detail not in repr(recorder.calls)
