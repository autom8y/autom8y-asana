"""Two-sided tests for the sprint-3 composite write tool (asana-mcp-v1).

THROWAWAY test suite (reference posture). Bootstraps `src` onto sys.path so the
non-shipped `asana_mcp` package imports without touching shared pyproject config.

Discriminating-canary posture (discriminating-canary-doctrine §2.1/§2.2): this is a
BUILD of a new surface, so the teeth are the standard two-sided controls —
  - POSITIVE control: valid input -> the chain completes / a partial failure CONVERGES
    on safe re-run (W-3).
  - NEGATIVE control: a deliberately-broken INPUT (empty tag_gid; a backing 404/500)
    is CORRECTLY REFUSED with an honest partial-state receipt.
NO defect is injected into the tool to manufacture a RED (that would be G-THEATER); the
RED comes only from breaking the INPUT the tool judges. The SAME harness flips
GREEN<->RED on input alone.

The backend fake serves RECORDED response shapes ({data, meta} envelopes) via
httpx.MockTransport — ZERO live Asana calls, and it models the SVR-7 verbs' IDEMPOTENT
semantics so convergence is observable.
"""

from __future__ import annotations

import json
import pathlib
import sys
import types
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

_SRC = pathlib.Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from asana_mcp.tools.composite_write import (  # noqa: E402
    TOOL_NAME,
    execute_composite_write,
    register,
    write_surface_enabled,
)


# --------------------------------------------------------------------------- #
# Local mount harness (test-only; sprint-2 owns the real skeleton)
# --------------------------------------------------------------------------- #
@dataclass
class _Ctx:
    http: Any
    settings: Any = None


class FakeMCP:
    """Records tool registrations; mirrors FastMCP's `.tool(name=, description=)` decorator."""

    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self, *, name: str, description: str | None = None):
        def _deco(fn):
            self.tools[name] = fn
            return fn

        return _deco


@dataclass
class RecordingBackend:
    """Programmable fake of the autom8y-asana REST surface (recorded {data,meta} shapes).

    Models SVR-7 backing verbs with IDEMPOTENT semantics (add_tag no-op if already tagged;
    PUT completed=true is true->true) so re-run convergence is observable. Records every
    request for double-apply assertions. `fail_next` queues forced non-2xx responses.
    """

    calls: list[tuple[str, str, dict]] = field(default_factory=list)
    tagged: set[str] = field(default_factory=set)
    completed: set[str] = field(default_factory=set)
    saved: dict[str, dict] = field(default_factory=dict)
    _fail: dict[tuple[str, str], list[int]] = field(default_factory=dict)

    def fail_next(self, method: str, path_contains: str, status_code: int, times: int = 1) -> None:
        self._fail.setdefault((method, path_contains), []).extend([status_code] * times)

    def _maybe_fail(self, method: str, path: str) -> int | None:
        for (m, sub), queue in self._fail.items():
            if m == method and sub in path and queue:
                return queue.pop(0)
        return None

    def handler(self, request: httpx.Request) -> httpx.Response:
        method = request.method
        path = request.url.path
        body = json.loads(request.content) if request.content else {}
        self.calls.append((method, path, body))

        forced = self._maybe_fail(method, path)
        if forced is not None:
            return httpx.Response(
                forced, json={"error": {"code": "FORCED", "message": f"forced {forced}"}}
            )

        # add_tag: POST /api/v1/tasks/{gid}/tags — idempotent no-op if already tagged
        if method == "POST" and path.endswith("/tags"):
            gid = path.split("/")[-2]
            self.tagged.add(gid)
            return httpx.Response(
                200, json={"data": {"gid": gid, "tag": body.get("tag_gid")}, "meta": {}}
            )

        # push / mark_complete: PUT /api/v1/tasks/{gid}
        if method == "PUT" and "/tasks/" in path:
            gid = path.split("/")[-1]
            if "completed" in body:
                (self.completed.add if body["completed"] else self.completed.discard)(gid)
            else:
                self.saved[gid] = body
            return httpx.Response(
                200, json={"data": {"gid": gid, "completed": gid in self.completed}, "meta": {}}
            )

        return httpx.Response(404, json={"error": {"code": "NOT_FOUND", "message": path}})


@pytest.fixture
async def ctx_factory():
    clients: list[httpx.AsyncClient] = []

    def _make(backend: RecordingBackend, *, enable_write: bool = True) -> _Ctx:
        client = httpx.AsyncClient(
            base_url="http://asana-rest.local", transport=httpx.MockTransport(backend.handler)
        )
        clients.append(client)
        return _Ctx(http=client, settings=types.SimpleNamespace(enable_write_surface=enable_write))

    yield _make
    for c in clients:
        await c.aclose()


# --------------------------------------------------------------------------- #
# POSITIVE control — the surface works
# --------------------------------------------------------------------------- #
async def test_happy_path_completes_all_three_steps(ctx_factory):
    backend = RecordingBackend()
    ctx = ctx_factory(backend)

    result = await execute_composite_write(
        ctx, task_gid="111", tag_gid="222", save_fields={"notes": "reviewed"}
    )

    assert result.status == "completed"
    assert result.committed == ["add_tag", "push", "mark_complete"]
    assert result.not_committed == []
    assert backend.tagged == {"111"} and backend.completed == {"111"}
    # order was enforced server-side
    assert [c[0] for c in backend.calls] == ["POST", "PUT", "PUT"]


async def test_partial_failure_then_rerun_converges(ctx_factory):
    """W-3: push fails once; committed=[add_tag]; unchanged re-run CONVERGES to completed."""
    backend = RecordingBackend()
    backend.fail_next("PUT", "/tasks/111", 500)  # first PUT (push) fails once
    ctx = ctx_factory(backend)

    r1 = await execute_composite_write(
        ctx, task_gid="111", tag_gid="222", save_fields={"notes": "x"}
    )
    assert r1.status == "refused_incomplete"
    assert r1.committed == ["add_tag"]
    assert backend.tagged == {"111"} and "111" not in backend.completed
    assert r1.rerun_guidance and "converge" in r1.rerun_guidance

    r2 = await execute_composite_write(
        ctx, task_gid="111", tag_gid="222", save_fields={"notes": "x"}
    )
    assert r2.status == "completed"
    assert r2.committed == ["add_tag", "push", "mark_complete"]
    assert backend.completed == {"111"}
    # convergence, NOT duplication: still tagged exactly once
    assert backend.tagged == {"111"}


async def test_idempotent_rerun_on_completed_state_is_noop_convergence(ctx_factory):
    backend = RecordingBackend()
    ctx = ctx_factory(backend)

    r1 = await execute_composite_write(ctx, task_gid="111", tag_gid="222")
    r2 = await execute_composite_write(ctx, task_gid="111", tag_gid="222")

    assert r1.status == r2.status == "completed"
    assert backend.tagged == {"111"} and backend.completed == {"111"}  # no double-apply


# --------------------------------------------------------------------------- #
# NEGATIVE control — broken INPUT is refused (teeth: same harness, flipped by input)
# --------------------------------------------------------------------------- #
async def test_broken_input_empty_tag_refused_before_any_call(ctx_factory):
    backend = RecordingBackend()
    ctx = ctx_factory(backend)

    result = await execute_composite_write(ctx, task_gid="111", tag_gid="   ")

    assert result.status == "refused_incomplete"
    assert result.committed == []
    assert backend.calls == []  # nothing attempted against the backend
    assert "refused pre-flight" in result.steps[0].detail


async def test_backing_404_on_step1_refuses_nothing_committed_no_atomicity_claim(ctx_factory):
    backend = RecordingBackend()
    backend.fail_next("POST", "/tags", 404)
    ctx = ctx_factory(backend)

    result = await execute_composite_write(ctx, task_gid="111", tag_gid="222")

    assert result.status == "refused_incomplete"
    assert result.committed == []
    add_tag = next(s for s in result.steps if s.name == "add_tag")
    assert add_tag.status == "failed" and add_tag.http_status == 404
    downstream = [s.status for s in result.steps if s.name in {"push", "mark_complete"}]
    assert downstream == ["not_attempted", "not_attempted"]
    # honesty: never claims atomicity the backing API cannot give
    assert "NON-ATOMIC" in result.atomicity


async def test_transport_exception_is_a_loud_refusal(ctx_factory):
    def _boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated transport failure")

    client = httpx.AsyncClient(base_url="http://x.local", transport=httpx.MockTransport(_boom))
    ctx = _Ctx(http=client, settings=types.SimpleNamespace(enable_write_surface=True))
    try:
        result = await execute_composite_write(ctx, task_gid="111", tag_gid="222")
    finally:
        await client.aclose()

    assert result.status == "refused_incomplete"
    assert "transport error" in result.steps[0].detail


# --------------------------------------------------------------------------- #
# Exposure gate — two-sided teeth on registration (default OFF; explicit ON)
# --------------------------------------------------------------------------- #
def test_register_is_gated_off_by_default(monkeypatch):
    monkeypatch.delenv("ASANA_MCP_ENABLE_WRITE_SURFACE", raising=False)
    mcp = FakeMCP()
    register(mcp, _Ctx(http=None, settings=None))
    assert mcp.tools == {}  # NOT exposed when unset


def test_register_exposes_only_when_enabled_via_settings():
    mcp = FakeMCP()
    register(mcp, _Ctx(http=None, settings=types.SimpleNamespace(enable_write_surface=True)))
    assert TOOL_NAME in mcp.tools


def test_register_exposes_when_enabled_via_env(monkeypatch):
    monkeypatch.setenv("ASANA_MCP_ENABLE_WRITE_SURFACE", "true")
    mcp = FakeMCP()
    register(mcp, _Ctx(http=None, settings=None))
    assert TOOL_NAME in mcp.tools


def test_settings_flag_false_overrides_env_true(monkeypatch):
    """Explicit settings.enable_write_surface=False wins over a truthy env var."""
    monkeypatch.setenv("ASANA_MCP_ENABLE_WRITE_SURFACE", "true")
    assert (
        write_surface_enabled(
            _Ctx(http=None, settings=types.SimpleNamespace(enable_write_surface=False))
        )
        is False
    )
