"""Test fixtures: faked HTTP (httpx.MockTransport) with envelope shapes transcribed
from autom8_asana/query/models.py + api/routes at HEAD f3d8eec1.

These fixtures NEVER hit live Asana and NEVER touch the live TokenManager — a fake
token provider + a MockTransport are injected through the build_context seams.
"""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest_asyncio
from asana_mcp.context import build_context
from asana_mcp.settings import Settings

# --- canned wire payloads (exact native envelope shapes) ----------------------

ENTITIES = [
    {
        "entity_type": "offer",
        "display_name": "Offer",
        "project_gid": "1200653012566782",
        "category": "business",
    },
    {
        "entity_type": "unit",
        "display_name": "Unit",
        "project_gid": "1201081073731555",
        "category": "business",
    },
]
OFFER_FIELDS = [
    {
        "name": "office_phone",
        "dtype": "str",
        "nullable": True,
        "description": "Office phone (E.164).",
    },
    {"name": "vertical", "dtype": "str", "nullable": True, "description": "Business vertical."},
    {
        "name": "classification",
        "dtype": "str",
        "nullable": False,
        "description": "Section classification.",
    },
]
OFFER_RELATIONS = [
    {
        "target": "unit",
        "direction": "child",
        "default_join_key": "unit_gid",
        "cardinality": "many_to_one",
        "description": "Offer's unit.",
    },
]
OFFER_SECTIONS = [
    {"section_name": "active", "classification": "active"},
    {"section_name": "inactive", "classification": "inactive"},
]
# rows: SuccessResponse[RowsResponse] DOUBLE envelope; honesty fields in inner meta.
ROWS_ENVELOPE = {
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
    "meta": {"request_id": "req-rows-1"},
}
# aggregate: AggregateMeta emits ONLY stale_served (no honest_empty/contract_complete).
AGG_ENVELOPE = {
    "data": {
        "data": [{"vertical": "dental", "count_office_phone": 5}],
        "meta": {
            "group_count": 1,
            "aggregation_count": 1,
            "group_by": ["vertical"],
            "entity_type": "offer",
            "project_gid": "1200653012566782",
            "query_ms": 8.1,
            "stale_served": True,
        },
    },
    "meta": {"request_id": "req-agg-1"},
}
RESOLVE_ENVELOPE = {
    "data": {
        "results": [
            {"gid": "1234567890123456", "match_count": 1},
            {"gid": None, "error": "NOT_FOUND", "match_count": 0},
        ],
        "meta": {
            "resolved_count": 1,
            "unresolved_count": 1,
            "entity_type": "unit",
            "project_gid": "1201081073731555",
            "available_fields": [],
            "criteria_schema": ["phone", "vertical"],
        },
    },
    "meta": {"request_id": "req-resolve-1"},
}
# GET /api/v1/workflows -> list_workflows: SuccessResponse[list[WorkflowEntry]] SINGLE
# envelope. Entries transcribed verbatim from the registered configs
# (lambda_handlers/{insights_export,conversation_audit}.py::_config) — the oracle
# carries NO side-effect field, so the disclosure tool states the write posture itself.
WORKFLOWS_ENVELOPE = {
    "data": [
        {
            "workflow_id": "insights-export",
            "log_prefix": "lambda_insights_export",
            "requires_data_client": True,
            "response_metadata_keys": ["total_tables_succeeded", "total_tables_failed"],
        },
        {
            "workflow_id": "conversation-audit",
            "log_prefix": "lambda_conversation_audit",
            "requires_data_client": True,
            "response_metadata_keys": ["truncated_count"],
        },
    ],
    "meta": {"request_id": "req-workflows-1", "timestamp": "2026-07-23T00:00:00Z"},
}


def _json(payload, status=200):
    return httpx.Response(status, json=payload)


def healthy_handler(request: httpx.Request) -> httpx.Response:
    m, p = request.method, request.url.path
    if p == "/ready":
        return _json({"status": "ready"})
    if m == "GET" and p == "/v1/query/entities":
        return _json({"data": ENTITIES})
    if m == "GET" and p == "/v1/query/offer/fields":
        return _json({"data": OFFER_FIELDS})
    if m == "GET" and p == "/v1/query/offer/relations":
        return _json({"data": OFFER_RELATIONS})
    if m == "GET" and p == "/v1/query/offer/sections":
        return _json({"data": OFFER_SECTIONS})
    if m == "POST" and p == "/v1/query/offer/rows":
        return _json(ROWS_ENVELOPE)
    if m == "POST" and p == "/v1/query/offer/aggregate":
        return _json(AGG_ENVELOPE)
    if m == "POST" and p == "/v1/resolve/unit":
        return _json(RESOLVE_ENVELOPE)
    if m == "GET" and p == "/api/v1/workflows/":
        return _json(WORKFLOWS_ENVELOPE)
    return _json({"error": {"code": "UNMAPPED_ROUTE"}}, status=404)


def readiness_cold_handler(request: httpx.Request) -> httpx.Response:
    # Every route (incl. /ready) is a warming 503 — the readiness gate must fire.
    return _json(
        {"error": {"code": "CACHE_NOT_WARMED"}, "details": {"retry_after_seconds": 30}}, status=503
    )


def endpoint_warming_handler(request: httpx.Request) -> httpx.Response:
    # /ready is healthy, but the tool endpoint returns a cold-frame 503.
    if request.url.path == "/ready":
        return _json({"status": "ready"})
    return _json(
        {"error": {"code": "CACHE_BUILD_IN_PROGRESS"}, "details": {"retry_after_seconds": 15}},
        status=503,
    )


def auth_fail_handler(request: httpx.Request) -> httpx.Response:
    # /ready is healthy, but the tool endpoint returns a 401 — DISTINCT from warming.
    if request.url.path == "/ready":
        return _json({"status": "ready"})
    return _json({"error": {"code": "SERVICE_TOKEN_REQUIRED"}}, status=401)


async def _fake_token() -> str:
    return "fake.s2s.jwt"


@pytest_asyncio.fixture
async def ctx_factory():
    """Yield a factory that builds a SidecarContext from a MockTransport handler."""
    created = []

    def _make(handler: Callable[[httpx.Request], httpx.Response]):
        settings = Settings(base_url="http://sat.local", ready_path="/ready")
        ctx = build_context(
            settings, token_provider=_fake_token, transport=httpx.MockTransport(handler)
        )
        created.append(ctx)
        return ctx

    yield _make
    for ctx in created:
        await ctx.http.aclose()


@pytest_asyncio.fixture
async def fake_ctx(ctx_factory):
    return ctx_factory(healthy_handler)


@pytest_asyncio.fixture
async def cold_ctx(ctx_factory):
    """Every route (incl. /ready) is a warming 503 — the readiness gate must fire."""
    return ctx_factory(readiness_cold_handler)


@pytest_asyncio.fixture
async def endpoint_warming_ctx(ctx_factory):
    """/ready healthy, but the tool endpoint returns a cold-frame 503."""
    return ctx_factory(endpoint_warming_handler)


@pytest_asyncio.fixture
async def auth_fail_ctx(ctx_factory):
    """/ready healthy, but the tool endpoint returns 401 (DISTINCT from warming)."""
    return ctx_factory(auth_fail_handler)
