"""The /ready outbound dependency cache: single-flight, TTL-bounded (D-AF3 part 1).

``/ready`` is unauthenticated and exempt from the rate limiter, and it makes an
outbound JWKS request. Policy under test:

- Only the outbound JWKS check is cached. A flood of ``/ready`` requests,
  concurrent or sequential within the TTL, makes at most one JWKS round per
  TTL. The local checks (preload state, workflow configs, bot PAT presence)
  run live on every call.
- A preload transition shows on the very next ``/ready``, inside a TTL window:
  503 while WARMING or FAILED, 200 when READY or DEGRADED.
- A check that raises is never cached, so it cannot be served as a success
  later. A failure result is cached like any result and expires at the TTL.

The dependency functions are replaced by counting fakes, and the cache clock is
a manual clock, so no request leaves the process and no test sleeps on the TTL.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import httpx
import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.health_models import CheckResult, HealthStatus
from autom8_asana.api.main import create_app
from autom8_asana.api.routes import health

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastapi import FastAPI

TTL = health.READY_DEPENDENCY_TTL_SECONDS
FLOOD = 20


class _ManualClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class _CountingCheck:
    """A dependency check that counts calls and returns or raises in sequence."""

    def __init__(self, *outcomes: CheckResult | Exception, delay: float = 0.0) -> None:
        self.calls = 0
        self._outcomes = list(outcomes)
        self._delay = delay

    async def __call__(self) -> CheckResult:
        self.calls += 1
        if self._delay:
            await asyncio.sleep(self._delay)
        outcome = self._outcomes[min(self.calls, len(self._outcomes)) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _ok() -> CheckResult:
    return CheckResult(status=HealthStatus.OK)


def _degraded(error: str) -> CheckResult:
    return CheckResult(status=HealthStatus.DEGRADED, detail={"error": error})


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> _ManualClock:
    manual = _ManualClock()
    monkeypatch.setattr(health._ready_jwks_cache, "_clock", manual)
    return manual


@pytest.fixture
def bot_pat_check(monkeypatch: pytest.MonkeyPatch) -> _CountingCheck:
    check = _CountingCheck(CheckResult(status=HealthStatus.OK, detail={"configured": True}))
    monkeypatch.setattr(health, "_probe_bot_pat", check)
    return check


@pytest.fixture
def serviceable() -> Iterator[None]:
    """Preload READY and workflow configs registered; restore both afterwards."""
    saved_state, saved_detail = health.get_preload_state(), health.get_preload_detail()
    saved_workflows = health.is_workflow_configs_registered()
    health.set_cache_ready(True)
    health.set_workflow_configs_registered(True)
    health.reset_readiness_dependency_cache()
    yield
    health._set_preload_state(saved_state, saved_detail)
    health._workflow_configs_registered = saved_workflows
    health.reset_readiness_dependency_cache()


@pytest.fixture
def app(serviceable: None) -> FastAPI:
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    # No context manager: the lifespan (startup discovery) is not needed.
    return TestClient(app, raise_server_exceptions=False)


def _jwks(client: TestClient) -> tuple[int, dict[str, object]]:
    response = client.get("/ready")
    return response.status_code, response.json()["checks"]["jwks"]


# ---------------------------------------------------------------------------
# One outbound round per TTL
# ---------------------------------------------------------------------------


def test_concurrent_ready_flood_shares_one_outbound_round(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch, bot_pat_check: _CountingCheck
) -> None:
    jwks_check = _CountingCheck(_ok(), delay=0.05)
    monkeypatch.setattr(health, "_probe_jwks", jwks_check)

    async def _flood() -> list[int]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://probe") as ac:
            responses = await asyncio.gather(*(ac.get("/ready") for _ in range(FLOOD)))
        return [r.status_code for r in responses]

    statuses = asyncio.run(_flood())

    assert statuses == [200] * FLOOD
    assert jwks_check.calls == 1
    # The local bot PAT check is not cached: it runs on every request.
    assert bot_pat_check.calls == FLOOD


def test_sequential_ready_flood_within_ttl_makes_one_outbound_round(
    client: TestClient,
    clock: _ManualClock,
    monkeypatch: pytest.MonkeyPatch,
    bot_pat_check: _CountingCheck,
) -> None:
    jwks_check = _CountingCheck(_ok())
    monkeypatch.setattr(health, "_probe_jwks", jwks_check)

    for step in range(FLOOD):
        clock.now = step * (TTL / (FLOOD + 1))
        assert client.get("/ready").status_code == 200

    assert jwks_check.calls == 1
    assert bot_pat_check.calls == FLOOD


def test_a_new_round_happens_after_the_ttl(
    client: TestClient,
    clock: _ManualClock,
    monkeypatch: pytest.MonkeyPatch,
    bot_pat_check: _CountingCheck,
) -> None:
    jwks_check = _CountingCheck(_ok())
    monkeypatch.setattr(health, "_probe_jwks", jwks_check)

    client.get("/ready")
    clock.now = TTL - 0.01
    client.get("/ready")
    assert jwks_check.calls == 1

    clock.now = TTL
    client.get("/ready")
    assert jwks_check.calls == 2


# ---------------------------------------------------------------------------
# Preload state is read live (critic term 1)
# ---------------------------------------------------------------------------


def test_preload_state_is_read_live_inside_a_ttl_window(
    client: TestClient,
    clock: _ManualClock,
    monkeypatch: pytest.MonkeyPatch,
    bot_pat_check: _CountingCheck,
) -> None:
    jwks_check = _CountingCheck(_ok())
    monkeypatch.setattr(health, "_probe_jwks", jwks_check)

    assert client.get("/ready").status_code == 200

    clock.now = TTL / 2
    health.set_cache_failed("test_failure")
    assert client.get("/ready").status_code == 503

    health.set_cache_ready(False)  # WARMING
    assert client.get("/ready").status_code == 503

    health.set_cache_degraded("test_degrade")
    assert client.get("/ready").status_code == 200

    health.set_cache_ready(True)
    assert client.get("/ready").status_code == 200

    # Every transition above was seen without a new outbound round.
    assert jwks_check.calls == 1


# ---------------------------------------------------------------------------
# Raises are never cached; failure results expire at the TTL (critic term 2)
# ---------------------------------------------------------------------------


def test_a_raising_check_is_not_cached(
    client: TestClient,
    clock: _ManualClock,
    monkeypatch: pytest.MonkeyPatch,
    bot_pat_check: _CountingCheck,
) -> None:
    jwks_check = _CountingCheck(RuntimeError("dependency check raised"), _ok())
    monkeypatch.setattr(health, "_probe_jwks", jwks_check)

    status, jwks = _jwks(client)
    assert status == 200
    assert jwks["status"] == "degraded"
    assert jwks["detail"] == {"error": "unexpected"}

    # Inside the same TTL window: the raise was not stored, so a new round runs.
    clock.now = TTL / 2
    _, jwks = _jwks(client)
    assert jwks_check.calls == 2
    assert jwks["status"] == "ok"


def test_a_raise_after_expiry_never_serves_the_old_success(
    client: TestClient,
    clock: _ManualClock,
    monkeypatch: pytest.MonkeyPatch,
    bot_pat_check: _CountingCheck,
) -> None:
    jwks_check = _CountingCheck(_ok(), RuntimeError("dependency check raised"), _ok())
    monkeypatch.setattr(health, "_probe_jwks", jwks_check)

    assert _jwks(client)[1]["status"] == "ok"

    clock.now = TTL + 1
    _, jwks = _jwks(client)
    assert jwks_check.calls == 2
    assert jwks["status"] == "degraded"

    # Still inside the window that opened at the raise: no cached result.
    clock.now = TTL + 1.5
    _, jwks = _jwks(client)
    assert jwks_check.calls == 3
    assert jwks["status"] == "ok"


def test_a_failure_result_expires_at_the_ttl(
    client: TestClient,
    clock: _ManualClock,
    monkeypatch: pytest.MonkeyPatch,
    bot_pat_check: _CountingCheck,
) -> None:
    jwks_check = _CountingCheck(_degraded("connection_error"), _ok())
    monkeypatch.setattr(health, "_probe_jwks", jwks_check)

    assert _jwks(client)[1]["status"] == "degraded"

    clock.now = TTL - 0.01
    assert _jwks(client)[1]["status"] == "degraded"
    assert jwks_check.calls == 1

    clock.now = TTL
    assert _jwks(client)[1]["status"] == "ok"
    assert jwks_check.calls == 2


# ---------------------------------------------------------------------------
# The cache primitive
# ---------------------------------------------------------------------------


def test_concurrent_waiters_share_a_raise_and_nothing_is_stored() -> None:
    cache: health._SingleFlightTTLCache[CheckResult] = health._SingleFlightTTLCache(
        TTL, clock=_ManualClock()
    )
    compute = _CountingCheck(RuntimeError("dependency check raised"), _ok(), delay=0.01)

    async def _run() -> list[CheckResult | BaseException]:
        first = await asyncio.gather(
            *(cache.get(compute) for _ in range(5)), return_exceptions=True
        )
        second = await cache.get(compute)
        return [*first, second]

    results = asyncio.run(_run())

    assert all(isinstance(r, RuntimeError) for r in results[:5])
    assert results[5].status == HealthStatus.OK  # type: ignore[union-attr]
    assert compute.calls == 2


def test_reset_hook_drops_the_cached_result(
    client: TestClient,
    clock: _ManualClock,
    monkeypatch: pytest.MonkeyPatch,
    bot_pat_check: _CountingCheck,
) -> None:
    jwks_check = _CountingCheck(_ok())
    monkeypatch.setattr(health, "_probe_jwks", jwks_check)

    client.get("/ready")
    health.reset_readiness_dependency_cache()
    client.get("/ready")

    assert jwks_check.calls == 2
