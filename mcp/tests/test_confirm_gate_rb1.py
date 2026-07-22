"""Two-sided tests for the RB-1 confirm-before-firing gate (operator ruling R5).

THROWAWAY test suite (reference posture), same mount discipline as the s3/WS-B2
composite suites. Bootstraps ``mcp/`` onto sys.path so the non-shipped
``asana_mcp`` package imports without touching shared pyproject config.

The gate's load-bearing property, asserted two-sided:
  - POSITIVE control: phase 1 (no token) refuses with a confirmation envelope
    and ZERO backend calls; phase 2 (valid token, identical intent) executes
    the unchanged chain exactly once.
  - NEGATIVE controls (teeth): a reused token, an unknown/garbage token, an
    expired token, and a token presented with ANY drifted argument are ALL
    refused with zero writes — and any known-token attempt burns the token
    (single-use, whatever the outcome).

Backend is a recording httpx.MockTransport fake of the satellite REST surface —
ZERO live Asana calls, fake token provider, no fastmcp dependency.
"""

from __future__ import annotations

import pathlib
import sys
import types
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1]  # mcp/ root
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from asana_mcp.tools.composite_write import (  # noqa: E402
    TOOL_DESCRIPTION,
    TOOL_NAME,
    register,
)
from asana_mcp.tools.confirm_gate import (  # noqa: E402
    REDEEM_EXPIRED,
    REDEEM_MISMATCH,
    REDEEM_OK,
    REDEEM_UNKNOWN,
    ConfirmationGate,
    intent_fingerprint,
)

TASK = "1209000000000001"
TAG = "1300000000000042"


# --------------------------------------------------------------------------- #
# Harness (self-contained per island idiom)
# --------------------------------------------------------------------------- #
class FakeMCP:
    """Records tool registrations; mirrors FastMCP's `.tool(name=, description=)`."""

    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self, *, name: str, description: str | None = None):
        def _deco(fn):
            self.tools[name] = fn
            return fn

        return _deco


@dataclass
class RecordingBackend:
    """Recording fake of the satellite REST surface (writes + read-back)."""

    calls: list[tuple[str, str]] = field(default_factory=list)
    tagged: set[str] = field(default_factory=set)

    def handler(self, request: httpx.Request) -> httpx.Response:
        m, p = request.method, request.url.path
        self.calls.append((m, p))
        if m == "POST" and p == f"/api/v1/tasks/{TASK}/tags":
            self.tagged.add(TAG)
            return httpx.Response(200, json={"data": {"gid": TASK}})
        if m == "PUT" and p == f"/api/v1/tasks/{TASK}":
            return httpx.Response(200, json={"data": {"gid": TASK}})
        if m == "GET" and p == f"/api/v1/tasks/{TASK}":
            tags = [{"gid": TAG, "name": "routing-label"}] if TAG in self.tagged else []
            return httpx.Response(200, json={"data": {"gid": TASK, "tags": tags}})
        return httpx.Response(404, json={"error": {"code": "UNMAPPED_ROUTE"}})

    @property
    def write_calls(self) -> list[tuple[str, str]]:
        return [(m, p) for (m, p) in self.calls if m in {"POST", "PUT"}]


@dataclass
class _Ctx:
    http: Any
    settings: Any = None


def _registered_tool(backend: RecordingBackend):
    """Register the write tool (surface enabled) over the recording backend."""
    mcp = FakeMCP()
    client = httpx.AsyncClient(
        base_url="http://sat.local", transport=httpx.MockTransport(backend.handler)
    )
    ctx = _Ctx(http=client, settings=types.SimpleNamespace(enable_write_surface=True))
    register(mcp, ctx)
    assert TOOL_NAME in mcp.tools
    return mcp.tools[TOOL_NAME], client


# --------------------------------------------------------------------------- #
# Gate unit mechanics (injectable clock — expiry deterministically forced)
# --------------------------------------------------------------------------- #
def test_gate_issue_redeem_ok_and_single_use():
    gate = ConfirmationGate(ttl_s=600.0)
    fp = intent_fingerprint(task_gid=TASK, tag_gid=TAG, tag_name=None, save_fields={})
    token = gate.issue(fp)
    assert gate.redeem(token, fp) == REDEEM_OK
    # single-use: the SAME token never redeems twice
    assert gate.redeem(token, fp) == REDEEM_UNKNOWN


def test_gate_expiry_via_injected_clock():
    now = [0.0]
    gate = ConfirmationGate(ttl_s=600.0, clock=lambda: now[0])
    fp = intent_fingerprint(task_gid=TASK, tag_gid=TAG, tag_name=None, save_fields={})
    token = gate.issue(fp)
    now[0] = 600.0  # exactly at expiry -> expired
    assert gate.redeem(token, fp) == REDEEM_EXPIRED
    # and burned: not redeemable even if the clock rolled back
    now[0] = 0.0
    assert gate.redeem(token, fp) == REDEEM_UNKNOWN


def test_gate_intent_mismatch_burns_the_token():
    gate = ConfirmationGate()
    fp_a = intent_fingerprint(task_gid=TASK, tag_gid=TAG, tag_name=None, save_fields={})
    fp_b = intent_fingerprint(
        task_gid=TASK, tag_gid=TAG, tag_name=None, save_fields={"notes": "drifted"}
    )
    token = gate.issue(fp_a)
    assert gate.redeem(token, fp_b) == REDEEM_MISMATCH
    # burned on the mismatch attempt — the original intent cannot ride it later
    assert gate.redeem(token, fp_a) == REDEEM_UNKNOWN


def test_gate_unknown_token():
    gate = ConfirmationGate()
    fp = intent_fingerprint(task_gid=TASK, tag_gid=TAG, tag_name=None, save_fields={})
    assert gate.redeem("garbage-token", fp) == REDEEM_UNKNOWN


def test_gate_pending_store_is_bounded():
    gate = ConfirmationGate(max_pending=4)
    fp = intent_fingerprint(task_gid=TASK, tag_gid=TAG, tag_name=None, save_fields={})
    tokens = [gate.issue(fp) for _ in range(10)]
    assert gate.pending_count() <= 4
    # the newest token still redeems; the evicted oldest does not
    assert gate.redeem(tokens[-1], fp) == REDEEM_OK
    assert gate.redeem(tokens[0], fp) == REDEEM_UNKNOWN


def test_fingerprint_binds_every_intent_field():
    base = dict(task_gid=TASK, tag_gid=TAG, tag_name=None, save_fields={"notes": "x"})
    fp = intent_fingerprint(**base)
    assert fp == intent_fingerprint(**base)  # deterministic
    for drift in (
        dict(base, task_gid="other"),
        dict(base, tag_gid="other"),
        dict(base, tag_gid=None, tag_name="Routing"),
        dict(base, save_fields={"notes": "y"}),
    ):
        assert intent_fingerprint(**drift) != fp


# --------------------------------------------------------------------------- #
# Exposed-surface behavior (the R5 pause, end to end over the fake backend)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_phase1_pauses_with_zero_backend_calls():
    backend = RecordingBackend()
    tool, client = _registered_tool(backend)
    try:
        result = await tool(task_gid=TASK, tag_gid=TAG)
    finally:
        await client.aclose()

    assert result["status"] == "confirmation_required"
    assert result["write"] is None and result["confirmation"] is None
    req = result["confirmation_request"]
    assert req["confirmation_token"]
    assert req["single_use"] is True
    assert "HUMAN" in req["instruction"]
    assert "ALL tags" in req["trigger_posture"]  # v1: all tags trigger-capable
    assert "add_tag" in req["what_will_fire"][0]
    assert backend.calls == []  # NOTHING fired — not even a read


@pytest.mark.asyncio
async def test_phase2_with_token_executes_the_chain_once():
    backend = RecordingBackend()
    tool, client = _registered_tool(backend)
    try:
        pause = await tool(task_gid=TASK, tag_gid=TAG, notes="close-out")
        token = pause["confirmation_request"]["confirmation_token"]
        result = await tool(task_gid=TASK, tag_gid=TAG, notes="close-out", confirmation_token=token)
    finally:
        await client.aclose()

    assert result["status"] == "completed"
    assert backend.write_calls == [
        ("POST", f"/api/v1/tasks/{TASK}/tags"),
        ("PUT", f"/api/v1/tasks/{TASK}"),
        ("PUT", f"/api/v1/tasks/{TASK}"),
    ]
    assert result["confirmation"]["tag_present"] is True  # PLAY-3 read-back intact


@pytest.mark.asyncio
async def test_reused_token_refuses_and_writes_nothing_more():
    backend = RecordingBackend()
    tool, client = _registered_tool(backend)
    try:
        pause = await tool(task_gid=TASK, tag_gid=TAG)
        token = pause["confirmation_request"]["confirmation_token"]
        first = await tool(task_gid=TASK, tag_gid=TAG, confirmation_token=token)
        writes_after_first = list(backend.write_calls)
        replay = await tool(task_gid=TASK, tag_gid=TAG, confirmation_token=token)
    finally:
        await client.aclose()

    assert first["status"] == "completed"
    assert replay["status"] == "confirmation_required"
    assert replay["confirmation_request"]["reason"] == REDEEM_UNKNOWN
    assert backend.write_calls == writes_after_first  # zero additional writes


@pytest.mark.asyncio
async def test_drifted_arguments_refuse_and_burn_the_token():
    backend = RecordingBackend()
    tool, client = _registered_tool(backend)
    try:
        pause = await tool(task_gid=TASK, tag_gid=TAG)
        token = pause["confirmation_request"]["confirmation_token"]
        # the yes was for TASK/TAG with no save fields; sneak a drifted write in
        drifted = await tool(task_gid=TASK, tag_gid=TAG, notes="sneaky", confirmation_token=token)
        # the burned token no longer works even for the ORIGINAL intent
        original = await tool(task_gid=TASK, tag_gid=TAG, confirmation_token=token)
    finally:
        await client.aclose()

    assert drifted["status"] == "confirmation_required"
    assert drifted["confirmation_request"]["reason"] == REDEEM_MISMATCH
    assert original["status"] == "confirmation_required"
    assert original["confirmation_request"]["reason"] == REDEEM_UNKNOWN
    assert backend.write_calls == []  # nothing EVER fired


@pytest.mark.asyncio
async def test_garbage_token_refuses_with_zero_writes():
    backend = RecordingBackend()
    tool, client = _registered_tool(backend)
    try:
        result = await tool(task_gid=TASK, tag_gid=TAG, confirmation_token="not-a-token")
    finally:
        await client.aclose()

    assert result["status"] == "confirmation_required"
    assert result["confirmation_request"]["reason"] == REDEEM_UNKNOWN
    assert backend.calls == []


@pytest.mark.asyncio
async def test_gate_guards_the_tag_name_selector_too():
    backend = RecordingBackend()
    tool, client = _registered_tool(backend)
    try:
        result = await tool(task_gid=TASK, tag_name="Routing Label")
    finally:
        await client.aclose()

    assert result["status"] == "confirmation_required"
    assert result["confirmation_request"]["tag_selector"] == {
        "tag_gid": None,
        "tag_name": "Routing Label",
    }
    # zero calls: name resolution deliberately waits until AFTER the human yes
    assert backend.calls == []


def test_description_carries_the_gate_contract():
    assert "CONFIRM-BEFORE-FIRING GATE" in TOOL_DESCRIPTION
    assert "confirmation_token" in TOOL_DESCRIPTION
    assert "HUMAN" in TOOL_DESCRIPTION
    assert "ALL tags" in TOOL_DESCRIPTION


def test_redeem_ok_constant_shape():
    # the closure treats REDEEM_OK as the ONLY pass-through outcome
    assert REDEEM_OK == "ok"
    assert len({REDEEM_OK, REDEEM_UNKNOWN, REDEEM_EXPIRED, REDEEM_MISMATCH}) == 4
