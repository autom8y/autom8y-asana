"""Discriminating-canary fixture for the mcp-island CI gate (FL-4).

POLARITY (read before citing an exit code):
    ``python -m pytest canary -q`` exiting **1** is the GREEN receipt — it
    means the deliberately-broken input below was CORRECTLY REJECTED by the
    real judging surface (the guard has teeth). Exit **0** means NO TEETH
    (alarm: the battery accepted a defective envelope). Exit **5** means
    vacuous collection (alarm: the canary itself is broken). The CI step in
    ``.github/workflows/test.yml`` (job ``mcp-island``) enforces rc==1 exactly.

Doctrine (discriminating-canary-doctrine §2.1/§2.2, Mode 1 — test-only canary
on a working surface): the RED comes from breaking the INPUT the surface
judges, NEVER from injecting a defect into working production code
(G-THEATER, forbidden). The broken input here is a rows envelope whose inner
``meta`` silently DROPS the SVR-5 honesty attestations (``stale_served`` /
``honest_empty`` / ``contract_complete``) — the exact drift class the
honesty-passthrough contract (C6/SVR-5) exists to catch: a satellite that
stops attesting must not pass silently.

Two-sided teeth (§2.3): the SAME battery runs against the clean envelope
(positive control — PASSES) and the broken envelope (negative control —
FAILS BY DESIGN). The battery flips GREEN<->RED on input alone.

This directory is OUTSIDE ``testpaths = ["tests"]`` (mcp/pyproject.toml), so
the normal suite run never collects it; only the dedicated CI canary step
(and ``just test-mcp``) invokes it explicitly.
"""

from __future__ import annotations

import copy
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx
import pytest_asyncio
from asana_mcp.context import SidecarContext, build_context
from asana_mcp.schemas import RowsArgs
from asana_mcp.settings import Settings
from asana_mcp.tools.query import query_rows_handler

# Clean wire payload — transcribed from tests/conftest.py ROWS_ENVELOPE (the
# SuccessResponse[RowsResponse] DOUBLE envelope; honesty fields in inner meta).
CLEAN_ROWS_ENVELOPE: dict[str, Any] = {
    "data": {
        "data": [{"office_phone": "+15551234567", "vertical": "dental"}],
        "meta": {
            "total_count": 1,
            "returned_count": 1,
            "limit": 100,
            "offset": 0,
            "entity_type": "offer",
            "project_gid": "1200653012566782",
            "query_ms": 12.3,
            "stale_served": False,
            "honest_contract_complete": True,
            "honest_empty": False,
            "contract_complete": True,
            "unservable_required_columns": [],
        },
    },
    "meta": {"request_id": "req-rows-canary-clean"},
}

# BROKEN input: identical envelope, but the SVR-5 honesty attestations are
# silently stripped from the inner meta. Rows still present, shape still
# parseable — ONLY the attestation contract is violated. A no-teeth battery
# (shape-matching, not substance-matching) would accept this.
BROKEN_ROWS_ENVELOPE: dict[str, Any] = copy.deepcopy(CLEAN_ROWS_ENVELOPE)
for _key in (
    "stale_served",
    "honest_contract_complete",
    "honest_empty",
    "contract_complete",
    "unservable_required_columns",
):
    del BROKEN_ROWS_ENVELOPE["data"]["meta"][_key]
BROKEN_ROWS_ENVELOPE["meta"] = {"request_id": "req-rows-canary-broken"}


def _handler_for(envelope: dict[str, Any]) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/ready":
            return httpx.Response(200, json={"status": "ready"})
        if request.method == "POST" and request.url.path == "/v1/query/offer/rows":
            return httpx.Response(200, json=envelope)
        return httpx.Response(404, json={"error": {"code": "UNMAPPED_ROUTE"}})

    return handler


async def _fake_token() -> str:
    return "fake.s2s.jwt"


@pytest_asyncio.fixture
async def ctx_factory() -> AsyncIterator[Callable[[dict[str, Any]], SidecarContext]]:
    created: list[SidecarContext] = []

    def _make(envelope: dict[str, Any]) -> SidecarContext:
        settings = Settings(base_url="http://sat.local", ready_path="/ready")
        ctx = build_context(
            settings,
            token_provider=_fake_token,
            transport=httpx.MockTransport(_handler_for(envelope)),
        )
        created.append(ctx)
        return ctx

    yield _make
    for ctx in created:
        await ctx.http.aclose()


def _svr5_battery(result: dict[str, Any]) -> None:
    """The REAL judging battery — transcribed from tests/test_query_tools.py
    (test_query_rows_unwraps_and_surfaces_honesty_top_level). Asserts the C6
    contract: honesty attestations lifted UNWRAPPED-and-VISIBLE to top level.
    """
    assert result["entity_type"] == "offer"
    assert result["rows"] == [{"office_phone": "+15551234567", "vertical": "dental"}]
    assert result["rows_count"] == 1
    # honesty attestations MUST be at TOP LEVEL (SVR-5) — KeyError here means
    # the satellite response carried no attestation and nothing was surfaced:
    assert result["stale_served"] is False
    assert result["honest_empty"] is False
    assert result["contract_complete"] is True


async def test_positive_control_clean_envelope_passes(ctx_factory):
    """POSITIVE control: the clean envelope satisfies the battery (proves the
    battery is satisfiable — a canary that can only fail proves nothing)."""
    ctx = ctx_factory(CLEAN_ROWS_ENVELOPE)
    result = await query_rows_handler(ctx, "offer", RowsArgs(select=["office_phone", "vertical"]))
    _svr5_battery(result)


async def test_broken_fixture_is_rejected_EXPECT_FAIL(ctx_factory):
    """NEGATIVE control — FAILS BY DESIGN when the guard has teeth.

    The broken envelope (honesty attestations stripped) goes through the SAME
    handler and the SAME battery. The battery MUST reject it (KeyError on the
    absent top-level attestation). pytest rc==1 on this module is therefore
    the teeth receipt; rc==0 means the gate would wave a defective mcp/ state
    through and MUST itself fail CI.
    """
    ctx = ctx_factory(BROKEN_ROWS_ENVELOPE)
    result = await query_rows_handler(ctx, "offer", RowsArgs(select=["office_phone", "vertical"]))
    _svr5_battery(result)
