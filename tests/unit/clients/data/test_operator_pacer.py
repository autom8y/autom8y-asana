"""WS-2 cure: bounded bisection + run-scoped pacer for the operator batch path.

Proves the drift-resilient bounded batch (TDD §5.2/§5.4) holds the two invariants
and the residual-risk register:

- PROOF-4: drift-free -> exactly ``I_op * ceil(N/100)`` calls (fast path intact);
  one drift office -> bounded ``O(drift . log N)`` calls, all owned offices served;
  sprinkled drift -> the aggregate cap holds and >=1 owned office still serves.
- RISK-3: <=100 chunking at N in {1, 100, 101, 250} (no silent 422).
- RISK-5: ONE shared counter across insights + recursion (not 4xB).
- RISK-7: Retry-After honored once on 429, then skip (partial), no SA fallback.
- RISK-9: grep-zero SA fleet-read inside the operator endpoint module.

The server's all-or-nothing route is modeled by a respx handler: a batch whose
offices are ALL owned -> 200 serving each; ANY non-owned office -> bare 404-as-oracle.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx

import autom8_asana.clients.data._endpoints.operator as operator_mod
from autom8_asana.clients.data._endpoints._pacer import (
    DEFAULT_RUN_BUDGET,
    DEFAULT_WINDOW_LIMIT,
    BudgetExhausted,
    OperatorCallPacer,
    retry_after_seconds,
)
from autom8_asana.clients.data._endpoints.operator import (
    OPERATOR_BATCH_CEILING,
    OPERATOR_BATCH_PATH,
)
from autom8_asana.clients.data.client import DataServiceClient
from autom8_asana.clients.data.config import DataServiceConfig

pytestmark = pytest.mark.usefixtures("enable_insights_feature")

_OPERATOR_TOKEN = "operator.bearer.token"  # noqa: S105 -- test fixture, not a real secret


async def _noop_sleep(_seconds: float) -> None:
    """A no-op async sleep so throttle/backoff tests run instantly."""
    return None


def _provider(token: str = _OPERATOR_TOKEN) -> MagicMock:
    prov = MagicMock()
    prov.get_token = AsyncMock(return_value=token)
    return prov


def _client() -> DataServiceClient:
    return DataServiceClient(
        config=DataServiceConfig(base_url="http://data.test.local"),
        operator_token_provider=_provider(),
    )


def _pacer(**kwargs: Any) -> OperatorCallPacer:
    kwargs.setdefault("sleep", _noop_sleep)
    return OperatorCallPacer(**kwargs)


def _phone_result(phone: str, rows: list[dict[str, Any]]) -> dict:
    return {
        "phone": phone,
        "status": "success",
        "data": {"result_type": "result", "data": rows, "meta": {}},
        "error": None,
        "cache_hit": False,
        "duration_ms": 1.0,
    }


def _op_envelope(per_office: dict[str, list[dict]]) -> dict:
    return {
        "data": {
            "insight": "account_level_stats",
            "total_phones": len(per_office),
            "successful": len(per_office),
            "failed": 0,
            "results": [_phone_result(p, rows) for p, rows in per_office.items()],
            "pair_results": None,
            "duration_ms": 5.0,
        },
        "meta": {"request_id": "req_test"},
    }


def _all_or_nothing_handler(owned: set[str]):
    """Model the data route: ALL-owned batch -> 200; ANY drift office -> bare 404."""

    def handler(request: httpx.Request) -> httpx.Response:
        phones = json.loads(request.content)["phones"]
        if phones and all(p in owned for p in phones):
            return httpx.Response(200, json=_op_envelope({p: [{"office": p}] for p in phones}))
        return httpx.Response(404)

    return handler


def _phones(n: int) -> list[str]:
    return [f"+1{i:09d}" for i in range(n)]


# --- PROOF-4: bisection bounds (two-sided) ---


class TestBisectionBounds:
    async def test_drift_free_one_call_per_chunk(self) -> None:
        """Drift-free O -> exactly ceil(N/100) calls per insight; all owned served."""
        owned = set(_phones(15))
        pacer = _pacer()
        client = _client()
        with respx.mock:
            route = respx.post(OPERATOR_BATCH_PATH).mock(side_effect=_all_or_nothing_handler(owned))
            async with client:
                out = await client.get_operator_insights_batch_async(
                    "account_level_stats", phones=sorted(owned), pacer=pacer
                )
        assert set(out) == owned  # every owned office served
        assert route.call_count == 1  # N=15 <= 100 drift-free -> ONE batch call
        assert pacer.spent == 1
        assert pacer.partial is False
        assert pacer.unreached == set()

    async def test_one_drift_office_bounded_and_owned_served(self) -> None:
        """One drift office among N -> bounded calls (<= 2*ceil(log2 N)+1), all owned served."""
        all_phones = _phones(15)
        drift = all_phones[7]
        owned = set(all_phones) - {drift}
        pacer = _pacer()
        client = _client()
        with respx.mock:
            route = respx.post(OPERATOR_BATCH_PATH).mock(side_effect=_all_or_nothing_handler(owned))
            async with client:
                out = await client.get_operator_insights_batch_async(
                    "account_level_stats", phones=all_phones, pacer=pacer
                )
        # Every OWNED office served; the drift office is absent (empty deck).
        assert set(out) == owned
        assert drift not in out
        # Bounded by the per-insight clustered-drift envelope (PROOF-4).
        envelope = 2 * math.ceil(math.log2(len(all_phones))) + 1
        assert route.call_count <= envelope
        assert pacer.spent == route.call_count
        # Drift is a DEFINITIVE answer -> NOT marked unreached (publishes empty).
        assert pacer.unreached == set()

    async def test_sprinkled_drift_cap_holds_and_serves_some_owned(self) -> None:
        """Interleaved drift -> aggregate cap holds; >=1 owned office still serves."""
        all_phones = _phones(12)
        owned = {p for i, p in enumerate(all_phones) if i % 2 == 0}  # every other office
        pacer = _pacer()
        client = _client()
        with respx.mock:
            respx.post(OPERATOR_BATCH_PATH).mock(side_effect=_all_or_nothing_handler(owned))
            async with client:
                out = await client.get_operator_insights_batch_async(
                    "account_level_stats", phones=all_phones, pacer=pacer
                )
        # The hard cap is never exceeded even under worst-case interleaved drift.
        assert pacer.spent <= DEFAULT_RUN_BUDGET
        # At least one owned office is served with rows (row_count>0 holds; coverage
        # may be partial under sprinkled drift -- RISK-2).
        served_with_rows = {p for p, rows in out.items() if rows}
        assert served_with_rows
        assert served_with_rows <= owned  # never serves a drift office


# --- RISK-5: ONE shared counter across insights + recursion ---


class TestAggregateBudgetSharedCounter:
    async def test_four_insights_share_one_counter_under_cap(self) -> None:
        """Four insight calls on ONE pacer -> aggregate wire count <= B_run (not 4xB)."""
        owned = set(_phones(15))
        pacer = _pacer()
        client = _client()
        names = [
            "account_level_stats",
            "offer_level_stats",
            "question_level_stats",
            "asset_level_stats",
        ]
        with respx.mock:
            route = respx.post(OPERATOR_BATCH_PATH).mock(side_effect=_all_or_nothing_handler(owned))
            async with client:
                for name in names:
                    await client.get_operator_insights_batch_async(
                        name, phones=sorted(owned), pacer=pacer
                    )
        # Drift-free: 4 insights x 1 chunk = 4 wire calls total, ONE shared counter.
        assert route.call_count == len(names)
        assert pacer.spent == len(names)
        assert pacer.spent <= DEFAULT_RUN_BUDGET

    async def test_budget_exhaustion_marks_unreached_and_stops(self) -> None:
        """When drift exhausts B_run, the run goes partial and unreached is recorded."""
        all_phones = _phones(64)
        owned = {p for i, p in enumerate(all_phones) if i % 2 == 0}  # heavy interleaved drift
        pacer = _pacer()
        client = _client()
        with respx.mock:
            respx.post(OPERATOR_BATCH_PATH).mock(side_effect=_all_or_nothing_handler(owned))
            async with client:
                out = await client.get_operator_insights_batch_async(
                    "account_level_stats", phones=all_phones, pacer=pacer
                )
        assert pacer.spent <= DEFAULT_RUN_BUDGET  # cap held
        assert pacer.partial is True  # honestly flagged partial
        assert pacer.unreached  # some offices were budget-skipped -> protected
        # Anything served is genuinely owned (never a drift office served).
        assert {p for p, rows in out.items() if rows} <= owned


# --- RISK-3: <=100 chunking ---


class TestChunking:
    @pytest.mark.parametrize("n", [1, 100, 101, 250])
    async def test_chunking_no_422_and_correct_call_count(self, n: int) -> None:
        """N in {1,100,101,250} drift-free -> ceil(N/100) calls, every office served."""
        owned = set(_phones(n))
        # Budget large enough to admit all chunks for the >100 cases (drift-free).
        pacer = _pacer(run_budget=20)
        client = _client()
        with respx.mock:
            route = respx.post(OPERATOR_BATCH_PATH).mock(side_effect=_all_or_nothing_handler(owned))
            async with client:
                out = await client.get_operator_insights_batch_async(
                    "account_level_stats", phones=sorted(owned), pacer=pacer
                )
        expected_chunks = math.ceil(n / OPERATOR_BATCH_CEILING)
        assert route.call_count == expected_chunks  # chunked, never one oversized 422
        assert set(out) == owned  # all offices served across chunks
        # Every wire request body respected the <=100 ceiling.
        for call in route.calls:
            body = json.loads(call.request.content)
            assert len(body["phones"]) <= OPERATOR_BATCH_CEILING


# --- RISK-7: Retry-After honored, then skip (partial), no SA fallback ---


class TestThrottleHandling:
    async def test_429_with_retry_after_honored_then_skipped(self) -> None:
        """A persistently-throttled sub-batch is retried once then skipped (partial)."""
        all_phones = _phones(4)
        owned = set(all_phones)
        pacer = _pacer()
        sleeps: list[float] = []

        async def _record_sleep(seconds: float) -> None:
            sleeps.append(seconds)

        pacer._sleep = _record_sleep  # type: ignore[attr-defined]
        client = _client()
        with respx.mock:
            data_route = respx.post("/api/v1/data-service/insights")
            respx.post(OPERATOR_BATCH_PATH).mock(
                return_value=httpx.Response(429, headers={"Retry-After": "2"})
            )
            async with client:
                out = await client.get_operator_insights_batch_async(
                    "account_level_stats", phones=all_phones, pacer=pacer
                )
        # Throttled the whole way -> nothing served, run partial, offices protected.
        assert out == {}
        assert pacer.partial is True
        assert set(all_phones) <= pacer.unreached
        # Retry-After (2s) was honored at least once (the bounded retry).
        assert sleeps and sleeps[0] == pytest.approx(2.0)
        # G-NO-FALLBACK: the SA fleet-read endpoint was NEVER touched.
        assert not data_route.called

    async def test_5xx_subbatch_skipped_not_raised_no_sa_fallback(self) -> None:
        """A transient 5xx on a sub-batch is skipped (protected), never raised/SA."""
        all_phones = _phones(4)
        pacer = _pacer()
        client = _client()
        with respx.mock:
            data_route = respx.post("/api/v1/data-service/insights")
            respx.post(OPERATOR_BATCH_PATH).mock(return_value=httpx.Response(503))
            async with client:
                out = await client.get_operator_insights_batch_async(
                    "account_level_stats", phones=all_phones, pacer=pacer
                )
        assert out == {}
        assert pacer.partial is True
        assert set(all_phones) <= pacer.unreached  # protected, not destroyed
        assert not data_route.called


# --- RISK-9: grep-zero SA fleet-read inside the operator endpoint ---


class TestNoSaFallbackStatic:
    def test_operator_module_has_zero_sa_fleet_read_in_code(self) -> None:
        """G-NO-FALLBACK: the operator endpoint emits NO SA fleet-read call.

        AST-grep (not raw string) so the G-NO-FALLBACK *docstring* that names the SA
        path as the thing it must NEVER do does not self-trip. Asserts the executable
        code contains: zero attribute accesses to the SA fleet-read methods, and zero
        non-docstring string literal naming the SA fleet-read route.
        """
        import ast

        tree = ast.parse(Path(operator_mod.__file__).read_text(encoding="utf-8"))

        # Collect docstring Constant nodes (module + every def/class) to exclude.
        docstrings: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                body = getattr(node, "body", [])
                if (
                    body
                    and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)
                ):
                    docstrings.add(id(body[0].value))

        sa_methods = {
            "get_appointments_async",
            "get_leads_async",
            "get_reconciliation_async",
            "get_insights_async",
            "_get_auth_token",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert node.attr not in sa_methods, (
                    f"operator.py must not call SA fleet-read method {node.attr!r}"
                )
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docstrings
            ):
                assert "data-service/insights" not in node.value, (
                    "operator.py must not name the SA fleet-read route in code"
                )


# --- Pacer unit behavior ---


class TestOperatorCallPacer:
    def test_default_ceiling_strictly_below_server_window(self) -> None:
        """PROOF-3 self-limit: the run budget (9) is strictly below the 10/min guard."""
        assert DEFAULT_RUN_BUDGET < DEFAULT_WINDOW_LIMIT
        assert DEFAULT_RUN_BUDGET == 9
        assert DEFAULT_WINDOW_LIMIT == 10

    async def test_acquire_increments_until_budget_then_raises(self) -> None:
        pacer = _pacer(run_budget=3)
        for _ in range(3):
            await pacer.acquire()
        assert pacer.spent == 3
        with pytest.raises(BudgetExhausted):
            await pacer.acquire()
        assert pacer.partial is True

    async def test_window_limit_paces_when_run_budget_raised(self) -> None:
        """With run_budget above the window, acquire waits for the window to drain."""
        clock = [0.0]
        slept: list[float] = []

        async def _sleep(seconds: float) -> None:
            slept.append(seconds)
            clock[0] += seconds

        pacer = OperatorCallPacer(
            run_budget=20,
            window_seconds=60.0,
            window_limit=2,
            sleep=_sleep,
            monotonic=lambda: clock[0],
        )
        # Two acquires fill the window with no wait; the third must wait ~60s.
        await pacer.acquire()
        await pacer.acquire()
        assert slept == []
        await pacer.acquire()
        assert slept and slept[0] == pytest.approx(60.0)

    def test_retry_after_seconds_parses_header(self) -> None:
        resp = httpx.Response(429, headers={"Retry-After": "7"})
        assert retry_after_seconds(resp) == 7

    def test_retry_after_seconds_absent_header_returns_none(self) -> None:
        resp = httpx.Response(429)
        assert retry_after_seconds(resp) is None

    async def test_honor_retry_after_clamps_to_max(self) -> None:
        slept: list[float] = []

        async def _sleep(seconds: float) -> None:
            slept.append(seconds)

        pacer = OperatorCallPacer(max_retry_after_seconds=5.0, sleep=_sleep)
        await pacer.honor_retry_after(httpx.Response(429, headers={"Retry-After": "999"}))
        assert slept == [5.0]  # clamped
